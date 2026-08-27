"""Streaming and continuous monitoring for the AccuRad PRD.

Provides high-level functions for continuous measurement polling,
automatic BLE keep-alive, and data logging to files.
"""

from __future__ import annotations

import csv
import json
import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from accurad.client import AccuRad
    from accurad.models.device_data import DeviceData

logger = logging.getLogger("accurad.streaming")

DEFAULT_MAX_CONSECUTIVE_ERRORS = 10


def stream_measurements(
    device: AccuRad,
    interval: float = 0.5,
    callback: Callable[[DeviceData], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    max_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS,
) -> Generator[DeviceData, None, None]:
    """Yield continuous measurements from the device.

    Polls the device at the given interval and yields each
    :class:`~accurad.models.device_data.DeviceData` result. The polling
    naturally keeps the BLE connection alive (each request resets the
    2.5s timeout).

    Args:
        device: Connected AccuRad client.
        interval: Seconds between each poll (default 0.5s).
        callback: Optional function called with each measurement.
        on_error: Optional function called when a poll fails.
            Receives the exception instance. If not provided, errors
            are logged and skipped.
        max_errors: Stop streaming after this many consecutive errors
            (default 10). Set to 0 for unlimited retries.

    Yields:
        DeviceData for each successful poll.

    Raises:
        AccuRadError: If *max_errors* consecutive errors are reached.

    Example:
        >>> for data in stream_measurements(device, interval=1.0):
        ...     print(f"{data.merged.dose_rate_usv_h:.4f} uSv/h")

    """
    logger.info("Starting measurement stream (interval=%.2fs)", interval)
    consecutive_errors = 0

    while device.is_connected:
        start = time.monotonic()

        try:
            data = device.get_measurements()
        except Exception as exc:
            consecutive_errors += 1
            logger.warning(
                "Stream poll failed (%d consecutive): %s",
                consecutive_errors, exc,
            )

            if on_error is not None:
                on_error(exc)

            if max_errors > 0 and consecutive_errors >= max_errors:
                logger.error(
                    "Stopping stream: %d consecutive errors",
                    consecutive_errors,
                )
                raise

            # Sleep before retry
            elapsed = time.monotonic() - start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            continue

        # Reset on success
        consecutive_errors = 0

        if callback is not None:
            callback(data)

        yield data

        # Sleep for the remainder of the interval
        elapsed = time.monotonic() - start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_active_logger: _MeasurementLogger | None = None
_logger_lock = threading.Lock()


class _MeasurementLogger:
    """Background thread that polls and logs measurements."""

    def __init__(
        self,
        device: AccuRad,
        path: str | Path,
        fmt: str,
        interval: float,
        on_error: Callable[[Exception], None] | None = None,
        max_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS,
    ) -> None:
        self._device = device
        self._path = str(path)
        self._format = fmt
        self._interval = interval
        self._on_error = on_error
        self._max_errors = max_errors
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the logging thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="accurad-logger",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the logging thread and wait for it to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _run(self) -> None:
        """Poll the device and write measurements to file."""
        if self._format == "csv":
            self._run_csv()
        else:
            self._run_json()

    def _handle_error(self, exc: Exception, consecutive: int) -> bool:
        """Handle a poll error. Return True to stop logging."""
        logger.warning(
            "Logger poll failed (%d consecutive): %s",
            consecutive, exc,
        )
        if self._on_error is not None:
            self._on_error(exc)
        if self._max_errors > 0 and consecutive >= self._max_errors:
            logger.error(
                "Logger stopping: %d consecutive errors",
                consecutive,
            )
            return True
        return False

    def _run_csv(self) -> None:
        """Log measurements as CSV rows."""
        consecutive_errors = 0

        with open(self._path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "timestamp",
                "dose_rate_usv_h",
                "count_rate_cps",
                "background_dose_rate_usv_h",
                "background_count_rate_cps",
                "level",
                "dose_usv",
                "dose_duration_s",
                "battery_percent",
                "measurement_id",
            ])

            while not self._stop_event.is_set():
                start = time.monotonic()
                try:
                    data = self._device.get_measurements()
                except Exception as exc:
                    if self._stop_event.is_set():
                        break
                    consecutive_errors += 1
                    if self._handle_error(exc, consecutive_errors):
                        break
                    elapsed = time.monotonic() - start
                    remaining = self._interval - elapsed
                    if remaining > 0:
                        self._stop_event.wait(timeout=remaining)
                    continue

                consecutive_errors = 0
                writer.writerow([
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    f"{data.merged.dose_rate_usv_h:.6f}",
                    f"{data.merged.count_rate_cps:.2f}",
                    f"{data.merged.background_dose_rate_usv_h:.6f}",
                    f"{data.merged.background_count_rate_cps:.2f}",
                    f"{data.merged.level:.1f}",
                    f"{data.dose.dose_usv:.6f}",
                    f"{data.dose.duration_s:.0f}",
                    data.battery.level_percent
                    if data.battery.level_percent is not None
                    else "",
                    data.measurement_id,
                ])
                fh.flush()

                elapsed = time.monotonic() - start
                remaining = self._interval - elapsed
                if remaining > 0:
                    self._stop_event.wait(timeout=remaining)

    def _run_json(self) -> None:
        """Log measurements as JSON lines (one object per line)."""
        consecutive_errors = 0

        with open(self._path, "w", encoding="utf-8") as fh:
            while not self._stop_event.is_set():
                start = time.monotonic()
                try:
                    data = self._device.get_measurements()
                except Exception as exc:
                    if self._stop_event.is_set():
                        break
                    consecutive_errors += 1
                    if self._handle_error(exc, consecutive_errors):
                        break
                    elapsed = time.monotonic() - start
                    remaining = self._interval - elapsed
                    if remaining > 0:
                        self._stop_event.wait(timeout=remaining)
                    continue

                consecutive_errors = 0
                record = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "dose_rate_usv_h": data.merged.dose_rate_usv_h,
                    "count_rate_cps": data.merged.count_rate_cps,
                    "background_dose_rate_usv_h": data.merged.background_dose_rate_usv_h,
                    "background_count_rate_cps": data.merged.background_count_rate_cps,
                    "level": data.merged.level,
                    "dose_usv": data.dose.dose_usv,
                    "dose_duration_s": data.dose.duration_s,
                    "battery_percent": data.battery.level_percent,
                    "measurement_id": data.measurement_id,
                }
                fh.write(json.dumps(record) + "\n")
                fh.flush()

                elapsed = time.monotonic() - start
                remaining = self._interval - elapsed
                if remaining > 0:
                    self._stop_event.wait(timeout=remaining)


def start_logging(
    device: AccuRad,
    path: str | Path,
    fmt: str = "csv",
    interval: float = 1.0,
    on_error: Callable[[Exception], None] | None = None,
    max_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS,
) -> _MeasurementLogger:
    """Start logging measurement data to a file in a background thread.

    Returns the logger object so callers can manage its lifecycle
    directly (preferred). Also registers it as the global active
    logger for backward-compatible :func:`stop_logging` calls.

    Args:
        device: Connected AccuRad client.
        path: Output file path.
        fmt: Output format — ``"csv"`` or ``"json"`` (JSON lines).
        interval: Seconds between each measurement poll.
        on_error: Optional callback invoked on each poll error.
        max_errors: Stop after this many consecutive errors (default 10).

    Returns:
        The started :class:`_MeasurementLogger` instance. Call
        ``logger.stop()`` to end the session.

    Raises:
        ValueError: If format is not "csv" or "json".
        RuntimeError: If a logging session is already active.

    """
    global _active_logger

    if fmt not in ("csv", "json"):
        msg = f"Unsupported format {fmt!r}. Use 'csv' or 'json'."
        raise ValueError(msg)

    with _logger_lock:
        if _active_logger is not None:
            msg = (
                "A logging session is already active. "
                "Call stop_logging() first."
            )
            raise RuntimeError(msg)

        file_logger = _MeasurementLogger(
            device, path, fmt, interval, on_error, max_errors,
        )
        file_logger.start()
        _active_logger = file_logger
        logger.info(
            "Logging started: %s (%s, %.1fs interval)",
            path, fmt, interval,
        )
        return file_logger


def stop_logging() -> None:
    """Stop the active logging session.

    Does nothing if no logging session is active.
    """
    global _active_logger

    with _logger_lock:
        if _active_logger is not None:
            _active_logger.stop()
            _active_logger = None
            logger.info("Logging stopped")
