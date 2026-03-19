"""USB Serial (COM port) transport for the AccuRad PRD.

Uses pyserial to communicate over the USB Virtual COM Port.
"""

from __future__ import annotations

import struct

import serial

from accurad._constants import (
    DEFAULT_READ_TIMEOUT_S,
    DEFAULT_WRITE_TIMEOUT_S,
    LEN_FIELD_SIZE,
    START_MARKER,
    START_MARKER_LENGTH,
)
from accurad.connection.base import AccuRadConnection
from accurad.exceptions import ReadTimeoutError, USBConnectionError


class SerialConnection(AccuRadConnection):
    """AccuRad connection over USB Virtual COM Port via pyserial.

    Args:
        port: COM port identifier (e.g. "COM3", "/dev/ttyUSB0").
        read_timeout: Read timeout in seconds.
        write_timeout: Write timeout in seconds.

    """

    def __init__(
        self,
        port: str,
        read_timeout: float = DEFAULT_READ_TIMEOUT_S,
        write_timeout: float = DEFAULT_WRITE_TIMEOUT_S,
    ) -> None:
        """Initialize serial connection parameters."""
        self._port = port
        self._read_timeout = read_timeout
        self._write_timeout = write_timeout
        self._serial: serial.Serial | None = None

    def connect(self) -> None:
        """Open the serial port and flush buffers."""
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=921600,
                timeout=self._read_timeout,
                write_timeout=self._write_timeout,
            )
            # Flush any stale data in buffers
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except serial.SerialException as exc:
            raise USBConnectionError(
                f"Failed to open serial port '{self._port}': {exc}"
            ) from exc

    def disconnect(self) -> None:
        """Close the serial port."""
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def send(self, data: bytes) -> None:
        """Send bytes over the serial port."""
        ser = self._ensure_connected()
        try:
            ser.write(data)
            ser.flush()
        except serial.SerialException as exc:
            raise USBConnectionError(f"Write failed: {exc}") from exc

    def receive(self, timeout: float | None = None) -> bytes:
        """Read a complete AccuRad frame from the serial port.

        Synchronizes on the ``#!AccuRad!#`` start marker, reads the LEN
        field, then reads the remaining bytes (ID + payload + CRC).

        Args:
            timeout: Override the default read timeout (seconds).

        Returns:
            Complete frame bytes.

        """
        ser = self._ensure_connected()

        if timeout is not None:
            original_timeout = ser.timeout
            ser.timeout = timeout

        try:
            # Synchronize on start marker
            marker_buf = bytearray()
            while True:
                byte = ser.read(1)
                if not byte:
                    raise ReadTimeoutError("Timeout waiting for start marker")
                marker_buf.append(byte[0])
                # Keep only the last START_MARKER_LENGTH bytes
                if len(marker_buf) > START_MARKER_LENGTH:
                    marker_buf = marker_buf[-START_MARKER_LENGTH:]
                if bytes(marker_buf) == START_MARKER:
                    break

            # Read LEN field (2 bytes, little-endian)
            len_bytes = ser.read(LEN_FIELD_SIZE)
            if len(len_bytes) < LEN_FIELD_SIZE:
                raise ReadTimeoutError("Timeout reading LEN field")
            frame_len: int = struct.unpack("<H", len_bytes)[0]

            # Read remaining: ID(2) + Payload(N) + CRC(2) = frame_len bytes
            remaining = ser.read(frame_len)
            if len(remaining) < frame_len:
                raise ReadTimeoutError(
                    f"Timeout reading frame body: expected {frame_len} bytes, "
                    f"got {len(remaining)}"
                )

            # Reconstruct the full frame
            return bytes(START_MARKER + len_bytes + remaining)

        finally:
            if timeout is not None:
                ser.timeout = original_timeout

    @property
    def is_connected(self) -> bool:
        """Return True if the serial port is open."""
        return self._serial is not None and self._serial.is_open

    def _ensure_connected(self) -> serial.Serial:
        """Return the serial port or raise if not connected."""
        if self._serial is None or not self._serial.is_open:
            raise USBConnectionError("Not connected. Call connect() first.")
        return self._serial
