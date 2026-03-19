"""Abstract base class for AccuRad PRD connections.

Both USB (serial) and Bluetooth (BLE) transports implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AccuRadConnection(ABC):
    """Abstract transport layer for communicating with an AccuRad PRD.

    Subclasses must implement the core I/O methods. The high-level
    :class:`~accurad.client.AccuRad` client uses this interface to stay
    transport-agnostic.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish the connection to the device.

        Raises:
            ConnectionError: If the connection cannot be established.
            ConnectionTimeoutError: If the connection times out.

        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection and release resources."""

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Send raw bytes to the device.

        Args:
            data: Bytes to transmit.

        Raises:
            ConnectionError: If the connection is not open.

        """

    @abstractmethod
    def receive(self, timeout: float | None = None) -> bytes:
        """Receive a complete response frame from the device.

        The implementation must handle synchronization on the start marker
        ``#!AccuRad!#`` and read enough bytes based on the LEN field.

        Args:
            timeout: Read timeout in seconds. None uses the default.

        Returns:
            Raw bytes of the complete frame (marker + LEN + ID + payload + CRC).

        Raises:
            ReadTimeoutError: If no response within the timeout period.
            ConnectionError: If the connection is not open.

        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the connection is currently open."""

    def __enter__(self) -> AccuRadConnection:
        """Support ``with`` statement — connect on entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Support ``with`` statement — disconnect on exit."""
        self.disconnect()
