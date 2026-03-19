"""Exception hierarchy for the AccuRad PRD API.

All exceptions inherit from :class:`AccuRadError` so callers can catch
a single base class for broad error handling.
"""

from __future__ import annotations


class AccuRadError(Exception):
    """Base exception for all AccuRad API errors."""


# ---------------------------------------------------------------------------
# Connection errors
# ---------------------------------------------------------------------------


class ConnectionError(AccuRadError):
    """Base class for connection-related errors."""


class USBConnectionError(ConnectionError):
    """Failed to open or communicate via USB COM port."""


class BluetoothConnectionError(ConnectionError):
    """Failed to open or communicate via Bluetooth BLE."""


class ConnectionTimeoutError(ConnectionError):
    """Connection attempt timed out."""


# ---------------------------------------------------------------------------
# Protocol errors
# ---------------------------------------------------------------------------


class ProtocolError(AccuRadError):
    """Base class for protocol-level parsing errors."""


class InvalidFrameError(ProtocolError):
    """Start marker absent or frame structure is malformed."""


class CRCMismatchError(ProtocolError):
    """Computed CRC does not match the CRC received in the frame."""

    def __init__(self, expected: int, received: int) -> None:
        """Initialize with expected and received CRC values."""
        self.expected = expected
        self.received = received
        super().__init__(
            f"CRC mismatch: computed 0x{expected:04X}, received 0x{received:04X}"
        )


class UnexpectedFrameIDError(ProtocolError):
    """Received frame ID does not match the expected request ID."""

    def __init__(self, expected: int, received: int) -> None:
        """Initialize with expected and received frame IDs."""
        self.expected = expected
        self.received = received
        super().__init__(
            f"Unexpected frame ID: expected {expected}, got {received}"
        )


class IncompleteFrameError(ProtocolError):
    """Frame is truncated — received fewer bytes than LEN indicates."""


# ---------------------------------------------------------------------------
# Device errors
# ---------------------------------------------------------------------------


class DeviceError(AccuRadError):
    """Base class for device-state errors."""


class DeviceNotInitializedError(DeviceError):
    """Device has not completed its initialization sequence."""


class DeviceNotReadyError(DeviceError):
    """Device has critical faults preventing reliable operation."""


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class ReadTimeoutError(AccuRadError):
    """Timed out waiting for a response from the device."""
