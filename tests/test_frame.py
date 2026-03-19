"""Tests for frame parsing and validation."""

from __future__ import annotations

import pytest

from accurad.exceptions import CRCMismatchError, IncompleteFrameError, InvalidFrameError
from accurad.protocol.frame import ParsedFrame, parse_frame


class TestParseFrame:
    """Frame parser tests against manual example frames."""

    def test_parse_device_info_frame(self, device_info_frame: bytes) -> None:
        """Parse the complete device info frame from the manual."""
        result = parse_frame(device_info_frame)
        assert isinstance(result, ParsedFrame)
        assert result.frame_id == 0
        assert len(result.payload) == 65

    def test_parse_device_data_frame(self, device_data_frame: bytes) -> None:
        """Parse the complete device data frame from the manual."""
        result = parse_frame(device_data_frame)
        assert isinstance(result, ParsedFrame)
        assert result.frame_id == 1
        assert len(result.payload) == 47

    def test_missing_start_marker(self) -> None:
        """Raise InvalidFrameError when start marker is absent."""
        with pytest.raises(InvalidFrameError):
            parse_frame(b"\x00\x01\x02\x03")

    def test_truncated_frame(self) -> None:
        """Raise IncompleteFrameError when data is cut short."""
        # Valid marker + LEN indicating more data than present
        marker = b"#!AccuRad!#"
        len_field = b"\x45\x00"  # LEN=69 but we only provide the marker + LEN
        with pytest.raises(IncompleteFrameError):
            parse_frame(marker + len_field)

    def test_corrupted_crc(self, device_info_frame: bytes) -> None:
        """Raise CRCMismatchError when CRC is tampered with."""
        corrupted = bytearray(device_info_frame)
        corrupted[-1] ^= 0xFF  # Flip bits in last CRC byte
        with pytest.raises(CRCMismatchError):
            parse_frame(bytes(corrupted))

    def test_garbage_before_marker(self, device_info_frame: bytes) -> None:
        """Parser should skip garbage bytes before the start marker."""
        garbage = b"\xFF\xFE\xFD\x00\x00"
        result = parse_frame(garbage + device_info_frame)
        assert result.frame_id == 0
        assert len(result.payload) == 65
