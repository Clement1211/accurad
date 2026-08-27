"""Exception hierarchy for the AccuRad PRD API.

All exceptions inherit from :class:`AccuRadError` so callers can catch
a single base class for broad error handling.
"""

from __future__ import annotations


class AccuRadError(Exception):
    """Base exception for all AccuRad API errors.

    Attributes:
        recoverable: Whether retrying the operation may succeed.
        suggestion: Human-readable hint for resolving the error.

    """

    recoverable: bool = False
    suggestion: str | None = None

    def __init__(
        self,
        message: str = "",
        *,
        recoverable: bool | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Initialize with optional recoverability and suggestion."""
        super().__init__(message)
        if recoverable is not None:
            self.recoverable = recoverable
        if suggestion is not None:
            self.suggestion = suggestion


# ---------------------------------------------------------------------------
# Connection errors
# ---------------------------------------------------------------------------


class ConnectionError(AccuRadError):
    """Base class for connection-related errors."""

    recoverable = False


class USBConnectionError(ConnectionError):
    """Failed to open or communicate via USB COM port."""

    suggestion = "Check that the device is plugged in and the COM port is correct."


class BluetoothConnectionError(ConnectionError):
    """Failed to open or communicate via Bluetooth BLE."""

    suggestion = (
        "Ensure the device is in discoverable mode "
        "(NFC tap or menu) and within range."
    )


class ConnectionTimeoutError(ConnectionError):
    """Connection attempt timed out."""

    recoverable = True
    suggestion = "The device may be busy. Try again or increase the timeout."


# ---------------------------------------------------------------------------
# Protocol errors
# ---------------------------------------------------------------------------


class ProtocolError(AccuRadError):
    """Base class for protocol-level parsing errors."""

    recoverable = False


class InvalidFrameError(ProtocolError):
    """Start marker absent or frame structure is malformed."""


class CRCMismatchError(ProtocolError):
    """Computed CRC does not match the CRC received in the frame."""

    recoverable = True
    suggestion = "Transient data corruption. Retry the request."

    def __init__(self, expected: int, received: int) -> None:
        """Initialize with expected and received CRC values."""
        self.expected = expected
        self.received = received
        super().__init__(
            f"CRC mismatch: computed 0x{expected:04X}, received 0x{received:04X}",
            recoverable=True,
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

    recoverable = True
    suggestion = "Partial data received. Retry the request."


class PayloadSizeMismatchError(ProtocolError):
    """Payload size does not match expected size for the frame ID."""

    def __init__(self, frame_id: int, expected: int, received: int) -> None:
        """Initialize with frame ID and size mismatch details."""
        self.frame_id = frame_id
        self.expected_size = expected
        self.received_size = received
        super().__init__(
            f"Frame ID={frame_id}: expected {expected}-byte payload, "
            f"got {received} bytes"
        )


# ---------------------------------------------------------------------------
# Device errors
# ---------------------------------------------------------------------------


class DeviceError(AccuRadError):
    """Base class for device-state errors."""


class DeviceNotInitializedError(DeviceError):
    """Device has not completed its initialization sequence."""

    recoverable = True
    suggestion = "Wait for the device to finish initializing (~30s after power-on)."


class DeviceNotReadyError(DeviceError):
    """Device has critical faults preventing reliable operation."""

    suggestion = "Check device hardware status via system_state flags."


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class ReadTimeoutError(AccuRadError):
    """Timed out waiting for a response from the device."""

    recoverable = True
    suggestion = "Device did not respond. Check connection and try again."
