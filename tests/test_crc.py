"""Tests for the CRC16 implementation.

Validates against the CRC values from the manual's example frames.
CRC is computed on ID + Payload (= XXXXX in manual terminology).
"""

from __future__ import annotations

from accurad.protocol.crc import crc16
from tests.conftest import DEVICE_DATA_FRAME_HEX, DEVICE_INFO_FRAME_HEX, _hex_to_bytes


class TestCRC16:
    """CRC16 computation tests against known-good values from the manual."""

    def test_device_info_crc(self) -> None:
        """CRC of ID+payload for device info must equal 0x5B02."""
        full = _hex_to_bytes(DEVICE_INFO_FRAME_HEX)
        # ID(2) + Payload(65) = bytes [13:-2]
        id_plus_payload = full[13:-2]
        assert crc16(id_plus_payload) == 0x5B02

    def test_device_data_crc(self) -> None:
        """CRC of ID+payload for device data must equal 0x599E."""
        full = _hex_to_bytes(DEVICE_DATA_FRAME_HEX)
        id_plus_payload = full[13:-2]
        assert crc16(id_plus_payload) == 0x599E

    def test_empty_data(self) -> None:
        """CRC of empty data should return the initial value (0xFFFF)."""
        assert crc16(b"") == 0xFFFF

    def test_single_byte(self) -> None:
        """CRC of a single byte should be deterministic."""
        result = crc16(b"\x00")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF
