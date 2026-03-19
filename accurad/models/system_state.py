"""SystemState model — 32-bit bitfield with alarm/fault utility methods.

Reference: protocol_reference.json -> bitfield_definitions -> system_state
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# Bit positions grouped by category
_ALARM_BITS: dict[str, int] = {
    "low_alarm": 7,
    "high_alarm": 8,
    "danger": 9,
    "dose_alarm": 10,
    "dose_danger": 11,
}

_FAULT_BITS: dict[str, int] = {
    "counting_fault": 0,
    "temp_sensor_fault": 1,
    "temp_out_of_range": 2,
    "magnetometer_fault": 17,
    "acc_gyrometer_fault": 18,
    "e2p_fault": 19,
    "flash_fault": 20,
    "audio_fault": 21,
    "ble_fault": 22,
}


@dataclass(frozen=True)
class SystemState:
    """Decoded system state word (32 bits, little-endian).

    Each attribute maps to a single bit in the raw uint32.
    Utility methods provide categorized access to alarms and faults.
    """

    # Faults (bits 0-2)
    counting_fault: bool
    temp_sensor_fault: bool
    temp_out_of_range: bool

    # Status (bits 3-6)
    check_datetime: bool
    accumulation_enabled: bool
    accumulation_in_progress: bool
    acknowledged: bool

    # Alarms (bits 7-11)
    low_alarm: bool
    high_alarm: bool
    danger: bool
    dose_alarm: bool
    dose_danger: bool

    # Modes (bits 12-13)
    low_power: bool
    search_mode: bool

    # Bit 15
    calibration_expired: bool

    # Bit 16
    vbs: bool

    # Hardware faults (bits 17-22)
    magnetometer_fault: bool
    acc_gyrometer_fault: bool
    e2p_fault: bool
    flash_fault: bool
    audio_fault: bool
    ble_fault: bool

    # Modes (bits 23-24)
    discreet: bool
    alarm_thresholds_not_consistent: bool

    # Control (bits 30-31)
    initialized: bool
    remote_ctrl: bool

    def has_alarms(self) -> bool:
        """Return True if any radiological alarm is active (bits 7-11)."""
        return any(
            getattr(self, name) for name in _ALARM_BITS
        )

    def has_faults(self) -> bool:
        """Return True if any hardware fault is detected."""
        return any(
            getattr(self, name) for name in _FAULT_BITS
        )

    def get_active_alarms(self) -> list[str]:
        """Return names of all active alarm flags."""
        return [name for name in _ALARM_BITS if getattr(self, name)]

    def get_active_faults(self) -> list[str]:
        """Return names of all active fault flags."""
        return [name for name in _FAULT_BITS if getattr(self, name)]

    def is_ready(self) -> bool:
        """Return True if device is initialized and has no critical faults."""
        return self.initialized and not self.has_faults()


def decode_system_state(data: bytes, offset: int = 0) -> SystemState:
    """Decode a 4-byte system state word from *data* at *offset*.

    Args:
        data: Raw bytes containing the system state uint32.
        offset: Byte offset into *data*.

    Returns:
        Fully decoded SystemState with all 32 flags.

    """
    raw: int = struct.unpack_from("<I", data, offset)[0]

    def _bit(n: int) -> bool:
        return bool(raw & (1 << n))

    return SystemState(
        counting_fault=_bit(0),
        temp_sensor_fault=_bit(1),
        temp_out_of_range=_bit(2),
        check_datetime=_bit(3),
        accumulation_enabled=_bit(4),
        accumulation_in_progress=_bit(5),
        acknowledged=_bit(6),
        low_alarm=_bit(7),
        high_alarm=_bit(8),
        danger=_bit(9),
        dose_alarm=_bit(10),
        dose_danger=_bit(11),
        low_power=_bit(12),
        search_mode=_bit(13),
        calibration_expired=_bit(15),
        vbs=_bit(16),
        magnetometer_fault=_bit(17),
        acc_gyrometer_fault=_bit(18),
        e2p_fault=_bit(19),
        flash_fault=_bit(20),
        audio_fault=_bit(21),
        ble_fault=_bit(22),
        discreet=_bit(23),
        alarm_thresholds_not_consistent=_bit(24),
        initialized=_bit(30),
        remote_ctrl=_bit(31),
    )
