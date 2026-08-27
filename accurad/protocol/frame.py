"""Frame parsing and validation for the AccuRad PRD protocol.

A response frame has this layout:

    #!AccuRad!# (11 bytes) | LEN (2 LE) | ID (2 LE) | Payload (N) | CRC (2 LE)
                             ◄─────────── LEN = N + 4 ──────────────►

CRITICAL: LEN includes ID(2) + Payload(N) + CRC(2) = N + 4.
Therefore: payload_size = LEN - 4, NOT LEN - 2.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

from accurad._constants import (
    DEVICE_DATA_PAYLOAD_SIZE,
    DEVICE_INFO_PAYLOAD_SIZE,
    ID_FIELD_SIZE,
    LEN_FIELD_SIZE,
    LEN_OVERHEAD,
    START_MARKER,
    START_MARKER_LENGTH,
)
from accurad.exceptions import (
    CRCMismatchError,
    IncompleteFrameError,
    InvalidFrameError,
    PayloadSizeMismatchError,
)
from accurad.protocol.crc import crc16

logger = logging.getLogger("accurad.protocol.frame")

_EXPECTED_PAYLOAD_SIZES: dict[int, int] = {
    0: DEVICE_INFO_PAYLOAD_SIZE,
    1: DEVICE_DATA_PAYLOAD_SIZE,
}


@dataclass(frozen=True)
class ParsedFrame:
    """Result of successfully parsing and validating a raw frame.

    Attributes:
        frame_id: The 16-bit frame ID (0 = device info, 1 = device data).
        payload: The raw payload bytes (CRC-validated).

    """

    frame_id: int
    payload: bytes


def parse_frame(data: bytes) -> ParsedFrame:
    """Parse and validate a complete AccuRad response frame.

    Steps:
        1. Locate and validate the ``#!AccuRad!#`` start marker.
        2. Extract LEN (2 bytes, little-endian).
        3. Extract ID (2 bytes, little-endian).
        4. Extract payload (LEN - 4 bytes).
        5. Extract CRC (2 bytes, little-endian).
        6. Validate CRC: ``crc16(id_bytes + payload) == received_crc``.

    Args:
        data: Raw bytes containing a complete response frame.

    Returns:
        A :class:`ParsedFrame` with the validated frame ID and payload.

    Raises:
        InvalidFrameError: If the start marker is missing or data is too short.
        IncompleteFrameError: If the frame is truncated.
        CRCMismatchError: If the computed CRC doesn't match.

    """
    logger.debug("Parsing frame (%d bytes): %s", len(data), data.hex())

    # 1. Find and validate start marker
    marker_pos = data.find(START_MARKER)
    if marker_pos == -1:
        logger.warning("Start marker not found in %d bytes", len(data))
        raise InvalidFrameError("Start marker '#!AccuRad!#' not found in data")

    # Position after the start marker
    pos = marker_pos + START_MARKER_LENGTH

    # 2. Extract LEN
    if len(data) < pos + LEN_FIELD_SIZE:
        raise IncompleteFrameError("Frame too short: missing LEN field")

    frame_len: int = struct.unpack_from("<H", data, pos)[0]
    pos += LEN_FIELD_SIZE

    # Validate we have enough data for the entire frame content
    # LEN covers: ID(2) + Payload(N) + CRC(2) = frame_len bytes
    if len(data) < pos + frame_len:
        raise IncompleteFrameError(
            f"Frame truncated: LEN={frame_len} but only "
            f"{len(data) - pos} bytes available after LEN field"
        )

    # 3. Extract ID (save raw bytes for CRC validation)
    id_pos = pos
    frame_id: int = struct.unpack_from("<H", data, pos)[0]
    pos += ID_FIELD_SIZE

    # 4. Extract payload
    payload_size = frame_len - LEN_OVERHEAD  # LEN - 4
    if payload_size < 0:
        raise InvalidFrameError(
            f"Invalid LEN={frame_len}: too small to contain ID + CRC"
        )

    payload = data[pos : pos + payload_size]
    pos += payload_size

    # 5. Extract received CRC
    received_crc: int = struct.unpack_from("<H", data, pos)[0]

    # 6. Validate CRC — computed on ID + payload (= "XXXXX" in manual terminology)
    id_plus_payload = data[id_pos : id_pos + ID_FIELD_SIZE + payload_size]
    computed_crc = crc16(id_plus_payload)
    logger.debug(
        "Frame ID=%d, payload=%d bytes, CRC computed=0x%04X received=0x%04X",
        frame_id, payload_size, computed_crc, received_crc,
    )
    if computed_crc != received_crc:
        logger.warning(
            "CRC mismatch: computed 0x%04X, received 0x%04X",
            computed_crc, received_crc,
        )
        raise CRCMismatchError(expected=computed_crc, received=received_crc)

    # 7. Validate payload size against expected size for known frame IDs
    expected_size = _EXPECTED_PAYLOAD_SIZES.get(frame_id)
    if expected_size is not None and payload_size != expected_size:
        logger.warning(
            "Payload size mismatch for ID=%d: expected %d, got %d",
            frame_id, expected_size, payload_size,
        )
        raise PayloadSizeMismatchError(
            frame_id=frame_id, expected=expected_size, received=payload_size,
        )

    logger.debug("Frame parsed OK: ID=%d, %d-byte payload", frame_id, payload_size)
    return ParsedFrame(frame_id=frame_id, payload=payload)


def find_frame_in_stream(buffer: bytearray) -> tuple[ParsedFrame | None, int]:
    """Attempt to find and parse a complete frame in a byte buffer.

    This is useful for stream-based reading where data arrives in chunks.
    It searches for the start marker and tries to parse a complete frame.

    Args:
        buffer: Mutable byte buffer that may contain partial or complete frames.

    Returns:
        A tuple of (parsed_frame_or_None, bytes_consumed).
        If a frame was found, bytes_consumed indicates how many bytes
        from the start of the buffer were used (including any garbage
        before the marker). If no complete frame is available yet,
        returns (None, bytes_to_discard) where bytes_to_discard is the
        number of bytes before the marker (or 0 if marker not found).

    """
    marker_pos = buffer.find(START_MARKER)
    if marker_pos == -1:
        # No marker found — safe to discard everything except the last
        # (START_MARKER_LENGTH - 1) bytes which could be a partial marker
        safe_discard = max(0, len(buffer) - START_MARKER_LENGTH + 1)
        return None, safe_discard

    # Check if we have enough data for at least the LEN field
    len_pos = marker_pos + START_MARKER_LENGTH
    if len(buffer) < len_pos + LEN_FIELD_SIZE:
        return None, marker_pos  # Discard bytes before marker

    frame_len: int = struct.unpack_from("<H", buffer, len_pos)[0]
    total_frame_size = START_MARKER_LENGTH + LEN_FIELD_SIZE + frame_len

    # Check if we have the complete frame
    if len(buffer) < marker_pos + total_frame_size:
        return None, marker_pos  # Discard bytes before marker, wait for more

    # We have a complete frame — try to parse it
    frame_bytes = bytes(buffer[marker_pos : marker_pos + total_frame_size])
    frame = parse_frame(frame_bytes)
    bytes_consumed = marker_pos + total_frame_size

    return frame, bytes_consumed
