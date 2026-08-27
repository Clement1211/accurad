"""AccuRad — high-level client for the AccuRad PRD radiation detector.

This is the main entry point for users of the library. It provides a
clean, transport-agnostic interface for reading device information
and measurement data.

Example:
    >>> from accurad import AccuRad
    >>> with AccuRad.connect_usb("COM3") as device:
    ...     info = device.get_device_info()
    ...     data = device.get_measurements()
    ...     print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} uSv/h")

"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

from accurad._constants import DEVICE_DATA_REQUEST, DEVICE_INFO_REQUEST
from accurad.connection.serial import SerialConnection
from accurad.exceptions import AccuRadError, UnexpectedFrameIDError
from accurad.protocol.frame import parse_frame
from accurad.protocol.parsers import parse_device_data, parse_device_info

if TYPE_CHECKING:
    from collections.abc import Callable

    from accurad.connection.base import AccuRadConnection
    from accurad.models.device_data import DeviceData
    from accurad.models.device_info import DeviceInfo

logger = logging.getLogger("accurad.client")


class AccuRad:
    """High-level client for communicating with an AccuRad PRD.

    Use the factory classmethods :meth:`connect_usb` or
    :meth:`connect_bluetooth` to create an instance. Supports the
    context manager protocol (``with`` statement).

    Args:
        connection: An established :class:`AccuRadConnection` transport.
        retries: Number of automatic retries on recoverable errors.
        retry_delay: Seconds to wait between retries.

    """

    def __init__(
        self,
        connection: AccuRadConnection,
        retries: int = 0,
        retry_delay: float = 0.5,
        auto_reconnect: bool = False,
    ) -> None:
        """Initialize with an established connection."""
        self._connection = connection
        self._retries = retries
        self._retry_delay = retry_delay
        self._auto_reconnect = auto_reconnect
        self._reconnect_count = 0
        self._max_reconnects = 3
        self._lock = threading.Lock()
        # Callbacks
        self.on_disconnect: Callable[[], None] | None = None
        self.on_reconnect: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def connect_usb(
        cls,
        port: str,
        read_timeout: float = 3.0,
        write_timeout: float = 1.0,
        retries: int = 0,
        retry_delay: float = 0.5,
    ) -> AccuRad:
        """Connect to an AccuRad PRD via USB COM port.

        Args:
            port: Serial port identifier (e.g. "COM3", "/dev/ttyUSB0").
            read_timeout: Read timeout in seconds.
            write_timeout: Write timeout in seconds.
            retries: Automatic retries on recoverable errors (0=none).
            retry_delay: Seconds between retries.

        Returns:
            Connected AccuRad client instance.

        """
        logger.info("Connecting via USB to %s", port)
        conn = SerialConnection(
            port=port,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        )
        conn.connect()
        return cls(conn, retries=retries, retry_delay=retry_delay)

    @classmethod
    def connect_bluetooth(
        cls,
        address: str,
        connect_timeout: float = 15.0,
        read_timeout: float = 3.0,
        retries: int = 0,
        retry_delay: float = 0.5,
        auto_reconnect: bool = False,
    ) -> AccuRad:
        """Connect to an AccuRad PRD via Bluetooth Low Energy.

        Includes the mandatory 1-second post-connect delay.

        Args:
            address: BLE MAC address or device name.
            connect_timeout: Connection timeout in seconds.
            read_timeout: Read timeout in seconds.
            retries: Automatic retries on recoverable errors (0=none).
            retry_delay: Seconds between retries.
            auto_reconnect: Auto-reconnect on BLE connection loss.

        Returns:
            Connected AccuRad client instance.

        """
        logger.info("Connecting via BLE to %s", address)
        from accurad.connection.bluetooth import BluetoothConnection

        conn = BluetoothConnection(
            address=address,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )
        conn.connect()
        return cls(
            conn,
            retries=retries,
            retry_delay=retry_delay,
            auto_reconnect=auto_reconnect,
        )

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    def get_device_info(self, timeout: float | None = None) -> DeviceInfo:
        """Request and return device information (frame ID=0).

        Args:
            timeout: Override default read timeout for this request.

        Returns:
            Device information including manufacturer, serial number,
            firmware version, and device clock.

        Raises:
            ProtocolError: If the response frame is invalid.
            CRCMismatchError: If the CRC check fails.
            ReadTimeoutError: If the device doesn't respond.

        """
        logger.debug("Requesting device info (frame ID=0)")
        raw = self._request(DEVICE_INFO_REQUEST, timeout=timeout)
        frame = parse_frame(raw)

        if frame.frame_id != 0:
            raise UnexpectedFrameIDError(expected=0, received=frame.frame_id)

        info = parse_device_info(frame.payload)
        logger.debug(
            "Device info: S/N %s, FW %s",
            info.serial_number, info.firmware_version,
        )
        return info

    def get_measurements(self, timeout: float | None = None) -> DeviceData:
        """Request and return current measurements (frame ID=1).

        Args:
            timeout: Override default read timeout for this request.

        Returns:
            Current measurements including dose rate, count rate,
            accumulated dose, battery status, and system state.

        Raises:
            ProtocolError: If the response frame is invalid.
            CRCMismatchError: If the CRC check fails.
            ReadTimeoutError: If the device doesn't respond.

        """
        logger.debug("Requesting measurements (frame ID=1)")
        raw = self._request(DEVICE_DATA_REQUEST, timeout=timeout)
        frame = parse_frame(raw)

        if frame.frame_id != 1:
            raise UnexpectedFrameIDError(expected=1, received=frame.frame_id)

        data = parse_device_data(frame.payload)
        logger.debug(
            "Measurements: dose_rate=%.4f uSv/h, count_rate=%.2f cps",
            data.merged.dose_rate_usv_h, data.merged.count_rate_cps,
        )
        return data

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        """Close the connection to the device."""
        logger.info("Disconnecting from device")
        self._connection.disconnect()

    @property
    def is_connected(self) -> bool:
        """Return True if the connection to the device is active."""
        return self._connection.is_connected

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> AccuRad:
        """Enter context — connection is already established."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context — disconnect from the device."""
        self.disconnect()

    def __repr__(self) -> str:
        """Return a string representation of the client."""
        status = "connected" if self.is_connected else "disconnected"
        return f"AccuRad({status})"

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @staticmethod
    def discover_usb() -> list[dict[str, str]]:
        """List available USB COM ports that may be an AccuRad PRD.

        Returns:
            List of dicts with ``"port"`` and ``"description"`` keys.

        """
        try:
            from serial.tools.list_ports import comports
        except ImportError:
            logger.warning("pyserial not installed — USB discovery unavailable")
            return []

        results: list[dict[str, str]] = []
        for p in comports():
            results.append({
                "port": p.device,
                "description": p.description or "",
            })
        logger.debug("USB discovery found %d ports", len(results))
        return results

    @staticmethod
    def discover_bluetooth(
        timeout: float = 10.0,
    ) -> list[dict[str, str]]:
        """Scan for AccuRad BLE devices in range.

        Filters for devices whose name starts with ``ACR``.

        Args:
            timeout: Scan duration in seconds.

        Returns:
            List of dicts with ``"address"`` and ``"name"`` keys.

        """
        try:
            import asyncio

            from bleak import BleakScanner
        except ImportError:
            logger.warning("bleak not installed — BLE discovery unavailable")
            return []

        async def _scan() -> list[dict[str, str]]:
            devices = await BleakScanner.discover(timeout=timeout)
            results: list[dict[str, str]] = []
            for d in devices:
                name = d.name or ""
                if name.upper().startswith("ACR"):
                    results.append({
                        "address": d.address,
                        "name": name,
                    })
            return results

        results = asyncio.run(_scan())
        logger.debug("BLE discovery found %d AccuRad devices", len(results))
        return results

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self, timeout: float = 1.0) -> bool:
        """Quick health check — try to read device info.

        Args:
            timeout: Timeout for the request.

        Returns:
            True if the device responded successfully.

        """
        try:
            self.get_device_info(timeout=timeout)
        except Exception:
            return False
        return True

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def wait_for_ready(
        self, timeout: float = 30.0, interval: float = 0.5,
    ) -> DeviceData:
        """Poll until the device reports ``is_ready()`` or timeout.

        Useful after power-on when the device needs ~30s to initialize.

        Args:
            timeout: Maximum wait time in seconds.
            interval: Polling interval in seconds.

        Returns:
            The first :class:`DeviceData` where ``system_state.is_ready()``.

        Raises:
            TimeoutError: If the device is not ready within *timeout*.

        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self.get_measurements()
            if data.system_state.is_ready():
                logger.info("Device is ready")
                return data
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(interval, remaining))
        msg = f"Device not ready after {timeout:.0f}s"
        raise TimeoutError(msg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        request_bytes: bytes,
        timeout: float | None = None,
    ) -> bytes:
        """Send a request and receive the response, with retry logic.

        Retries only on recoverable errors (``exc.recoverable is True``),
        such as :class:`ReadTimeoutError` or :class:`CRCMismatchError`.
        Non-recoverable errors (e.g. ``ProtocolError``,
        ``ConnectionError``) are raised immediately.

        Args:
            request_bytes: Raw request frame to send.
            timeout: Override the default read timeout.

        Returns:
            Raw response bytes.

        """
        last_exc: Exception | None = None

        with self._lock:
            for attempt in range(1 + self._retries):
                try:
                    self._connection.send(request_bytes)
                    raw = self._connection.receive(timeout=timeout)
                    self._reconnect_count = 0
                    return raw
                except AccuRadError as exc:
                    last_exc = exc

                    # Auto-reconnect for BLE connection errors
                    if (
                        self._auto_reconnect
                        and not exc.recoverable
                        and self._reconnect_count < self._max_reconnects
                        and self._try_reconnect()
                    ):
                        continue

                    if not exc.recoverable or attempt >= self._retries:
                        raise
                    logger.warning(
                        "Request failed (attempt %d/%d): %s — retrying",
                        attempt + 1, 1 + self._retries, exc,
                    )
                    time.sleep(self._retry_delay)

        # Should not be reached, but satisfy type checker
        raise last_exc  # type: ignore[misc]

    def _try_reconnect(self) -> bool:
        """Attempt to reconnect the underlying transport.

        Returns:
            True if reconnection succeeded.

        """
        self._reconnect_count += 1
        logger.warning(
            "Attempting reconnect (%d/%d)",
            self._reconnect_count, self._max_reconnects,
        )
        try:
            self._connection.disconnect()
            self._connection.connect()
            logger.info("Reconnected successfully")
            if self.on_reconnect is not None:
                self.on_reconnect()
            return True
        except Exception:
            logger.error("Reconnect failed", exc_info=True)
            if self.on_disconnect is not None:
                self.on_disconnect()
            return False
