"""Tests for SystemState decoding and utility methods."""

from __future__ import annotations

import struct

from accurad.models.system_state import decode_system_state


class TestDecodeSystemState:
    """SystemState bitfield decoder tests."""

    def test_initialized_only(self) -> None:
        """0x40000000 = bit 30 only -> initialized=True, everything else False."""
        data = struct.pack("<I", 0x40000000)
        state = decode_system_state(data)
        assert state.initialized is True
        assert state.remote_ctrl is False
        assert state.has_alarms() is False
        assert state.has_faults() is False
        assert state.is_ready() is True

    def test_alarm_bits(self) -> None:
        """Set bits 7-11 (all alarms) + bit 30 (initialized)."""
        raw = (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10) | (1 << 11) | (1 << 30)
        data = struct.pack("<I", raw)
        state = decode_system_state(data)
        assert state.has_alarms() is True
        assert len(state.get_active_alarms()) == 5
        assert "low_alarm" in state.get_active_alarms()
        assert "danger" in state.get_active_alarms()

    def test_fault_bits(self) -> None:
        """Set counting_fault (bit 0) and ble_fault (bit 22)."""
        raw = (1 << 0) | (1 << 22) | (1 << 30)
        data = struct.pack("<I", raw)
        state = decode_system_state(data)
        assert state.has_faults() is True
        assert state.counting_fault is True
        assert state.ble_fault is True
        assert state.is_ready() is False  # has faults

    def test_zero_state(self) -> None:
        """All-zero state: nothing initialized, no alarms, no faults."""
        data = struct.pack("<I", 0)
        state = decode_system_state(data)
        assert state.initialized is False
        assert state.is_ready() is False  # not initialized
        assert state.get_active_alarms() == []
        assert state.get_active_faults() == []
