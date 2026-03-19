"""Shared test fixtures — hex dumps from the AccuRad manual (pages 115-119).

These are the authoritative test vectors. Every parser test MUST
validate against these exact bytes and expected decoded values.
"""

from __future__ import annotations

import pytest

# -----------------------------------------------------------------------
# Raw frame bytes from the manual examples
# -----------------------------------------------------------------------

# Device Info frame (ID=0) — manual page 117
# Full frame: marker(11) + LEN(2) + ID(2) + payload(65) + CRC(2) = 82 bytes
DEVICE_INFO_FRAME_HEX = (
    "23 21 41 63 63 75 52 61 64 21 23"  # #!AccuRad!#
    " 45 00"                              # LEN = 69
    " 00 00"                              # ID = 0
    " 4D 41 4E 55 46 41 43 54 55 52 45 52 00 00 00 00"  # "MANUFACTURER"
    " 4E 4F 4D 30 30 34 35 33 37 2D 43 00 00 00 00 00"  # "NOM004537-C"
    " 30 30 30 30 32 34 00 00 00 00 00 00 00 00 00 00"  # "000024"
    " 0B 06 00 00"                        # Firmware number = 1547
    " 00 00 01 01"                        # Firmware version = 1.1.0.0
    " EE 41 68 06"                        # Time_t = 14:15:08.820
    " C1 42 7E 00"                        # Date_t = 2020-02-24 (Monday)
    " 0E"                                 # Timezone index = 14
    " 02 5B"                              # CRC = 0x5B02
)

# Device Data frame (ID=1) — manual page 118
# Full frame: marker(11) + LEN(2) + ID(2) + payload(47) + CRC(2) = 64 bytes
DEVICE_DATA_FRAME_HEX = (
    "23 21 41 63 63 75 52 61 64 21 23"  # #!AccuRad!#
    " 33 00"                              # LEN = 51
    " 01 00"                              # ID = 1
    " 81"                                 # Merged state = 0x81
    " D7 86 4E 3D"                        # Dose rate = 0.050421562
    " E8 0A E5 40"                        # Count rate = 7.15758133
    " 13 39 13 3D"                        # BG dose rate = 0.0359431021
    " 4F 69 E8 40"                        # BG count rate = 7.262855
    " FE D9 61 3E"                        # Level = 0.220558137
    " 2B CD 27 00"                        # Dose time_t
    " C1 42 7E 00"                        # Dose date_t
    " F6 BE FA 3D"                        # Dose uSv = 0.122434542
    " 00 34 12 46"                        # Dose duration = 9357.0
    " A4"                                 # Battery state = 0xA4
    " 60"                                 # Battery level = 96%
    " 00 00 00 40"                        # System state = 0x40000000
    " 32 92 00 00"                        # Measurement ID = 37426
    " 9E 59"                              # CRC = 0x599E (manual has 4F A9 — doc error)
)


def _hex_to_bytes(hex_str: str) -> bytes:
    """Convert a space-separated hex string to bytes."""
    return bytes.fromhex(hex_str.replace(" ", ""))


@pytest.fixture()
def device_info_frame() -> bytes:
    """Complete raw device info frame (82 bytes)."""
    return _hex_to_bytes(DEVICE_INFO_FRAME_HEX)


@pytest.fixture()
def device_data_frame() -> bytes:
    """Complete raw device data frame (64 bytes)."""
    return _hex_to_bytes(DEVICE_DATA_FRAME_HEX)


@pytest.fixture()
def device_info_payload() -> bytes:
    """Just the 65-byte payload from the device info frame (no marker/LEN/ID/CRC)."""
    full = _hex_to_bytes(DEVICE_INFO_FRAME_HEX)
    # Skip: marker(11) + LEN(2) + ID(2) = 15 bytes
    # Payload: 65 bytes, CRC: 2 bytes at end
    return full[15:-2]


@pytest.fixture()
def device_data_payload() -> bytes:
    """Just the 47-byte payload from the device data frame."""
    full = _hex_to_bytes(DEVICE_DATA_FRAME_HEX)
    return full[15:-2]
