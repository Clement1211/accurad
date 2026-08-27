"""Bluetooth Low Energy (BLE) transport for the AccuRad PRD.

Uses the ``bleak`` library for cross-platform BLE communication.
Implements the mandatory post-connect delay and keep-alive heartbeat.

This module is only available when the ``bluetooth`` extra is installed:
    pip install accurad[bluetooth]
"""

from __future__ import annotations

import asyncio
import logging
import struct
import threading
import time

from accurad._constants import (
    BLE_KEEPALIVE_INTERVAL_S,
    BLE_POST_CONNECT_DELAY_S,
    BLE_UART_TX_UUID,
    DEFAULT_BLE_CONNECT_TIMEOUT_S,
    DEFAULT_READ_TIMEOUT_S,
    LEN_FIELD_SIZE,
    START_MARKER,
    START_MARKER_LENGTH,
)
from accurad.connection.base import AccuRadConnection
from accurad.exceptions import BluetoothConnectionError, ReadTimeoutError

logger = logging.getLogger("accurad.connection.bluetooth")

try:
    from bleak import BleakClient, BleakScanner
    from bleak.exc import BleakError

    _BLEAK_AVAILABLE = True
except ImportError:
    _BLEAK_AVAILABLE = False


def _require_bleak() -> None:
    """Raise ImportError if bleak is not installed."""
    if not _BLEAK_AVAILABLE:
        msg = (
            "Bluetooth support requires the 'bleak' package. "
            "Install it with: pip install accurad[bluetooth]"
        )
        raise ImportError(msg)


class BluetoothConnection(AccuRadConnection):
    """AccuRad connection over Bluetooth Low Energy (BLE) via bleak.

    Runs an asyncio event loop in a background thread so that BLE
    notifications are processed correctly on all platforms.

    Args:
        address: BLE MAC address or device name.
        connect_timeout: Connection timeout in seconds.
        read_timeout: Read timeout in seconds.

    """

    def __init__(
        self,
        address: str,
        connect_timeout: float = DEFAULT_BLE_CONNECT_TIMEOUT_S,
        read_timeout: float = DEFAULT_READ_TIMEOUT_S,
        keepalive: bool = True,
    ) -> None:
        """Initialize BLE connection parameters.

        Args:
            address: BLE MAC address or device name.
            connect_timeout: Connection timeout in seconds.
            read_timeout: Read timeout in seconds.
            keepalive: Auto-send heartbeat to prevent BLE disconnect.

        """
        _require_bleak()
        self._address = address
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._keepalive_enabled = keepalive
        self._client: BleakClient | None = None
        self._rx_buffer = bytearray()
        self._rx_event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._keepalive_timer: threading.Timer | None = None
        self._last_send_time: float = 0.0
        self._connected = False

    def connect(self) -> None:
        """Connect to the AccuRad PRD via BLE.

        Starts a background event loop thread, scans for the device,
        connects, and waits the mandatory 1-second post-connect delay.
        """
        # Start a dedicated event loop in a background thread
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever,
            name="accurad-ble-loop",
            daemon=True,
        )
        self._thread.start()

        # Run the async connect on the background loop
        future = asyncio.run_coroutine_threadsafe(
            self._async_connect(), self._loop
        )
        future.result(timeout=self._connect_timeout + 15.0)

    async def _async_connect(self) -> None:
        """Async implementation of BLE connect."""
        self._rx_event = asyncio.Event()

        # Scan first to get a BLEDevice object (required on Windows WinRT)
        logger.info(
            "Scanning for BLE device %s (timeout=%ss)",
            self._address, self._connect_timeout,
        )
        try:
            device = await BleakScanner.find_device_by_address(
                self._address, timeout=self._connect_timeout
            )
        except (BleakError, OSError) as exc:
            logger.error("BLE scan failed for '%s': %s", self._address, exc)
            raise BluetoothConnectionError(
                f"BLE scan failed for '{self._address}': {exc}"
            ) from exc

        if device is None:
            logger.error("BLE device '%s' not found", self._address)
            raise BluetoothConnectionError(
                f"Device '{self._address}' not found. "
                "Make sure it is in discoverable mode."
            )

        logger.info("BLE device found: %s (%s)", device.name, device.address)
        self._client = BleakClient(device, timeout=self._connect_timeout)

        try:
            await self._client.connect()
        except (BleakError, OSError) as exc:
            logger.error("BLE connect failed for '%s': %s", self._address, exc)
            raise BluetoothConnectionError(
                f"Failed to connect to '{self._address}': {exc}"
            ) from exc

        # Subscribe to notifications on the TX characteristic
        await self._client.start_notify(
            BLE_UART_TX_UUID,
            self._notification_handler,
        )
        logger.debug("Subscribed to BLE UART TX notifications")

        # MANDATORY: Wait 1 second after connect before first request
        # (PRD.md N4 — omitting this causes intermittent failures)
        logger.debug("Post-connect delay: %.1fs", BLE_POST_CONNECT_DELAY_S)
        await asyncio.sleep(BLE_POST_CONNECT_DELAY_S)

        self._connected = True
        self._last_send_time = time.monotonic()
        logger.info("BLE connected to %s", self._address)

        # Start keep-alive timer if enabled
        if self._keepalive_enabled:
            self._start_keepalive()

    def _notification_handler(
        self, _sender: object, data: bytearray
    ) -> None:
        """Handle incoming BLE notifications."""
        self._rx_buffer.extend(data)
        if self._rx_event is not None:
            self._rx_event.set()

    def _start_keepalive(self) -> None:
        """Schedule the next keep-alive check."""
        if not self._connected:
            return
        self._keepalive_timer = threading.Timer(
            BLE_KEEPALIVE_INTERVAL_S,
            self._keepalive_tick,
        )
        self._keepalive_timer.daemon = True
        self._keepalive_timer.start()

    def _keepalive_tick(self) -> None:
        """Send heartbeat if idle too long, then reschedule."""
        if not self._connected or self._loop is None:
            return
        if self.needs_keepalive:
            logger.debug("Sending BLE keep-alive heartbeat")
            try:
                from accurad._constants import DEVICE_DATA_REQUEST

                future = asyncio.run_coroutine_threadsafe(
                    self._async_send(DEVICE_DATA_REQUEST), self._loop,
                )
                future.result(timeout=2.0)
            except Exception:
                logger.warning("Keep-alive send failed", exc_info=True)
        self._start_keepalive()

    def _stop_keepalive(self) -> None:
        """Cancel the keep-alive timer."""
        if self._keepalive_timer is not None:
            self._keepalive_timer.cancel()
            self._keepalive_timer = None

    def disconnect(self) -> None:
        """Disconnect from the BLE device and stop the event loop."""
        logger.info("Disconnecting BLE from %s", self._address)
        self._stop_keepalive()
        if self._loop is not None and self._client is not None:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._client.disconnect(), self._loop
                )
                future.result(timeout=5.0)
            except Exception:
                pass

        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)

        self._client = None
        self._loop = None
        self._thread = None
        self._connected = False
        self._rx_buffer.clear()

    def send(self, data: bytes) -> None:
        """Send bytes to the device via BLE write."""
        if not self._connected or self._loop is None:
            raise BluetoothConnectionError(
                "Not connected. Call connect() first."
            )
        future = asyncio.run_coroutine_threadsafe(
            self._async_send(data), self._loop
        )
        future.result(timeout=5.0)

    async def _async_send(self, data: bytes) -> None:
        """Async implementation of BLE send."""
        logger.debug("BLE TX %d bytes: %s", len(data), data.hex())
        try:
            await self._client.write_gatt_char(  # type: ignore[union-attr]
                BLE_UART_TX_UUID,
                data,
                response=False,
            )
            self._last_send_time = time.monotonic()
        except (BleakError, OSError) as exc:
            logger.error("BLE write failed: %s", exc)
            raise BluetoothConnectionError(
                f"BLE write failed: {exc}"
            ) from exc

    def receive(self, timeout: float | None = None) -> bytes:
        """Receive a complete AccuRad frame from BLE notifications.

        Args:
            timeout: Read timeout in seconds.

        Returns:
            Complete frame bytes.

        """
        if not self._connected or self._loop is None:
            raise BluetoothConnectionError(
                "Not connected. Call connect() first."
            )
        effective_timeout = (
            timeout if timeout is not None else self._read_timeout
        )
        future = asyncio.run_coroutine_threadsafe(
            self._async_receive(effective_timeout), self._loop
        )
        return future.result(timeout=effective_timeout + 2.0)

    async def _async_receive(self, timeout: float) -> bytes:
        """Async implementation of frame reception from BLE buffer."""
        if self._rx_event is None:
            raise BluetoothConnectionError("RX event not initialized")

        deadline = time.monotonic() + timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ReadTimeoutError("Timeout waiting for BLE response")

            # Check buffer for a complete frame
            marker_pos = self._rx_buffer.find(START_MARKER)
            if marker_pos != -1:
                # Discard bytes before marker
                if marker_pos > 0:
                    del self._rx_buffer[:marker_pos]

                # Need at least marker + LEN to know frame size
                header_end = START_MARKER_LENGTH + LEN_FIELD_SIZE
                if len(self._rx_buffer) >= header_end:
                    frame_len = struct.unpack_from(
                        "<H", self._rx_buffer, START_MARKER_LENGTH
                    )[0]
                    total_size = (
                        START_MARKER_LENGTH + LEN_FIELD_SIZE + frame_len
                    )

                    if len(self._rx_buffer) >= total_size:
                        frame_data = bytes(self._rx_buffer[:total_size])
                        del self._rx_buffer[:total_size]
                        logger.debug("BLE RX %d bytes: %s", len(frame_data), frame_data.hex())
                        return frame_data

            # Wait for more data
            self._rx_event.clear()
            try:
                await asyncio.wait_for(
                    self._rx_event.wait(), timeout=remaining
                )
            except asyncio.TimeoutError:
                raise ReadTimeoutError(
                    "Timeout waiting for BLE response"
                ) from None

    @property
    def is_connected(self) -> bool:
        """Return True if the BLE connection is active."""
        return self._connected

    @property
    def seconds_since_last_send(self) -> float:
        """Seconds elapsed since the last data was sent to the device."""
        if self._last_send_time == 0.0:
            return 0.0
        return time.monotonic() - self._last_send_time

    @property
    def needs_keepalive(self) -> bool:
        """Return True if a keep-alive heartbeat should be sent now."""
        return self.seconds_since_last_send >= BLE_KEEPALIVE_INTERVAL_S
