"""Fixed request byte sequences for the AccuRad PRD.

These sequences are pre-computed and MUST be sent as-is.
Do NOT reconstruct them — the device expects these exact bytes.

Reference: protocol_reference.json -> requests
"""

from __future__ import annotations

from accurad._constants import DEVICE_DATA_REQUEST, DEVICE_INFO_REQUEST

__all__ = [
    "DEVICE_DATA_REQUEST",
    "DEVICE_INFO_REQUEST",
    "get_request_bytes",
]


def get_request_bytes(frame_id: int) -> bytes:
    """Return the fixed request bytes for a given frame ID.

    Args:
        frame_id: 0 for device info, 1 for device measurements.

    Returns:
        Raw bytes to send to the device.

    Raises:
        ValueError: If *frame_id* is not 0 or 1.

    """
    if frame_id == 0:
        return DEVICE_INFO_REQUEST
    if frame_id == 1:
        return DEVICE_DATA_REQUEST
    msg = f"Unknown frame ID: {frame_id}. Only 0 (info) and 1 (data) are supported."
    raise ValueError(msg)
