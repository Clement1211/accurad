"""Payload parsers — convert raw payload bytes into typed dataclasses.

Each parser corresponds to a specific frame ID:
- ``parse_device_info(payload)`` for ID=0
- ``parse_device_data(payload)`` for ID=1

Reference: protocol_reference.json -> payloads
"""

from __future__ import annotations

import struct

from accurad._constants import (
    DEVICE_DATA_PAYLOAD_SIZE,
    DEVICE_INFO_PAYLOAD_SIZE,
    TIMEZONE_TABLE,
)
from accurad.exceptions import ProtocolError
from accurad.models.datetime import decode_datetime
from accurad.models.device_data import (
    BatteryData,
    BatteryState,
    DeviceData,
    DoseData,
    MergedMeasurement,
    MergedState,
)
from accurad.models.device_info import DeviceInfo
from accurad.models.enums import MeasurementOrigin
from accurad.models.system_state import decode_system_state


def parse_device_info(payload: bytes) -> DeviceInfo:
    """Parse a 65-byte device info payload (frame ID=0).

    Layout:
        Offset  Size  Field
        0       16    Manufacturer (string, zero-terminated)
        16      16    Part Number (string, zero-terminated)
        32      16    Serial Number (string, zero-terminated)
        48      4     Firmware Number (uint32 LE)
        52      4     Firmware Version (uint32 LE -> AA.BB.CC.DD)
        56      4     Time_t (bitfield)
        60      4     Date_t (bitfield)
        64      1     Timezone Index (uint8)

    Args:
        payload: Raw payload bytes (must be exactly 65 bytes).

    Returns:
        Populated DeviceInfo dataclass.

    Raises:
        ProtocolError: If payload size is incorrect.

    """
    if len(payload) != DEVICE_INFO_PAYLOAD_SIZE:
        raise ProtocolError(
            f"Device info payload: expected {DEVICE_INFO_PAYLOAD_SIZE} bytes, "
            f"got {len(payload)}"
        )

    # Strings: read 16 bytes, decode ASCII, strip null terminators
    manufacturer = _decode_string(payload, 0, 16)
    part_number = _decode_string(payload, 16, 16)
    serial_number = _decode_string(payload, 32, 16)

    # Firmware
    firmware_number: int = struct.unpack_from("<I", payload, 48)[0]
    firmware_version_raw: int = struct.unpack_from("<I", payload, 52)[0]
    firmware_version = _format_firmware_version(firmware_version_raw)

    # DateTime (Time_t at offset 56, Date_t at offset 60)
    timezone_index: int = payload[64]
    device_datetime = decode_datetime(payload, offset=56, timezone_index=timezone_index)

    timezone_label = TIMEZONE_TABLE.get(timezone_index, f"Unknown ({timezone_index})")

    return DeviceInfo(
        manufacturer=manufacturer,
        part_number=part_number,
        serial_number=serial_number,
        firmware_number=firmware_number,
        firmware_version=firmware_version,
        device_datetime=device_datetime,
        timezone_index=timezone_index,
        timezone_label=timezone_label,
    )


def parse_device_data(payload: bytes) -> DeviceData:
    """Parse a 47-byte device data payload (frame ID=1).

    Layout:
        Offset  Size  Field
        0       1     Merged State (uint8 bitfield)
        1       4     Dose Rate uSv/h (float32 LE)
        5       4     Count Rate cps (float32 LE)
        9       4     Background Dose Rate uSv/h (float32 LE)
        13      4     Background Count Rate cps (float32 LE)
        17      4     Level 0-9 (float32 LE)
        21      4     Dose Time_t (bitfield)
        25      4     Dose Date_t (bitfield)
        29      4     Dose uSv (float32 LE)
        33      4     Dose Duration s (float32 LE)
        37      1     Battery State (uint8 bitfield)
        38      1     Battery Level % (uint8)
        39      4     System State (uint32 LE bitfield)
        43      4     Measurement ID (uint32 LE)

    Args:
        payload: Raw payload bytes (must be exactly 47 bytes).

    Returns:
        Populated DeviceData dataclass.

    Raises:
        ProtocolError: If payload size is incorrect.

    """
    if len(payload) != DEVICE_DATA_PAYLOAD_SIZE:
        raise ProtocolError(
            f"Device data payload: expected {DEVICE_DATA_PAYLOAD_SIZE} bytes, "
            f"got {len(payload)}"
        )

    # --- Merged Measurement ---
    merged_state_byte: int = payload[0]
    merged_state = MergedState(
        origin=MeasurementOrigin(merged_state_byte & 0x03),
        prd_15kev_incoherence=bool(merged_state_byte & 0x04),
        overload=bool(merged_state_byte & 0x40),
        initialized=bool(merged_state_byte & 0x80),
    )

    (dose_rate, count_rate, bg_dose_rate, bg_count_rate, level) = struct.unpack_from(
        "<5f", payload, 1
    )

    merged = MergedMeasurement(
        state=merged_state,
        dose_rate_usv_h=dose_rate,
        count_rate_cps=count_rate,
        background_dose_rate_usv_h=bg_dose_rate,
        background_count_rate_cps=bg_count_rate,
        level=level,
    )

    # --- Dose Data ---
    dose_datetime = decode_datetime(payload, offset=21)
    dose_usv: float = struct.unpack_from("<f", payload, 29)[0]
    dose_duration: float = struct.unpack_from("<f", payload, 33)[0]

    dose = DoseData(
        dose_datetime=dose_datetime,
        dose_usv=dose_usv,
        duration_s=dose_duration,
    )

    # --- Battery ---
    battery_state_byte: int = payload[37]
    battery_state = BatteryState(
        level_too_low=bool(battery_state_byte & 0x01),
        level_critical=bool(battery_state_byte & 0x02),
        usb_connected=bool(battery_state_byte & 0x04),
        failure=bool(battery_state_byte & 0x40),
        initialized=bool(battery_state_byte & 0x80),
    )

    raw_battery_level: int = payload[38]

    # Business rule: battery % is unreliable when USB is connected
    battery_level: int | None = None if battery_state.usb_connected else raw_battery_level

    battery = BatteryData(
        state=battery_state,
        level_percent=battery_level,
    )

    # --- System State ---
    system_state = decode_system_state(payload, offset=39)

    # --- Measurement ID ---
    measurement_id: int = struct.unpack_from("<I", payload, 43)[0]

    return DeviceData(
        merged=merged,
        dose=dose,
        battery=battery,
        system_state=system_state,
        measurement_id=measurement_id,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decode_string(data: bytes, offset: int, length: int) -> str:
    """Decode a zero-terminated ASCII string from a fixed-width field."""
    raw = data[offset : offset + length]
    # Find null terminator
    null_pos = raw.find(b"\x00")
    if null_pos != -1:
        raw = raw[:null_pos]
    return raw.decode("ascii", errors="replace")


def _format_firmware_version(raw: int) -> str:
    """Format a uint32 firmware version as 'AA.BB.CC.DD'.

    The raw value 0x00000101 becomes "0.0.1.1".
    """
    aa = (raw >> 24) & 0xFF
    bb = (raw >> 16) & 0xFF
    cc = (raw >> 8) & 0xFF
    dd = raw & 0xFF
    return f"{aa}.{bb}.{cc}.{dd}"
