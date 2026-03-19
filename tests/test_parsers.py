"""Tests for payload parsers — DeviceInfo and DeviceData.

Validates every decoded field against the manual's example values.
"""

from __future__ import annotations

import math

from accurad.models.enums import MeasurementOrigin
from accurad.protocol.parsers import parse_device_data, parse_device_info


class TestParseDeviceInfo:
    """Device info parser (ID=0) tests."""

    def test_manufacturer(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        assert info.manufacturer == "MANUFACTURER"

    def test_part_number(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        assert info.part_number == "NOM004537-C"

    def test_serial_number(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        assert info.serial_number == "000024"

    def test_firmware_number(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        assert info.firmware_number == 1547

    def test_firmware_version(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        # 0x00000101 -> "0.0.1.1"
        # Wait — manual says version is "1.1.0.0" but raw bytes are 00 00 01 01
        # 0x00000101: AA=0x00, BB=0x00, CC=0x01, DD=0x01 -> "0.0.1.1"
        # The manual decoded value "1.1.0.0" suggests bytes are 01 01 00 00 = 0x01010000
        # But raw is 00 00 01 01 LE -> uint32 = 0x01010000 -> AA=1, BB=1, CC=0, DD=0
        assert info.firmware_version == "1.1.0.0"

    def test_timezone(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        assert info.timezone_index == 14
        assert "UTC+00:00" in info.timezone_label

    def test_datetime_components(self, device_info_payload: bytes) -> None:
        info = parse_device_info(device_info_payload)
        dt = info.device_datetime
        assert dt.year == 2020
        assert dt.month == 2
        assert dt.day == 24
        assert dt.hour == 14
        assert dt.minute == 15
        assert dt.second == 8


class TestParseDeviceData:
    """Device data parser (ID=1) tests."""

    def test_merged_state(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert data.merged.state.initialized is True
        assert data.merged.state.origin == MeasurementOrigin.LOW_RANGE
        assert data.merged.state.overload is False

    def test_dose_rate(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert math.isclose(data.merged.dose_rate_usv_h, 0.050421562, rel_tol=1e-6)

    def test_count_rate(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert math.isclose(data.merged.count_rate_cps, 7.15758133, rel_tol=1e-5)

    def test_background_dose_rate(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert math.isclose(
            data.merged.background_dose_rate_usv_h, 0.0359431021, rel_tol=1e-5
        )

    def test_level(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert math.isclose(data.merged.level, 0.220558137, rel_tol=1e-5)

    def test_dose_usv(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert math.isclose(data.dose.dose_usv, 0.122434542, rel_tol=1e-5)

    def test_dose_duration(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert math.isclose(data.dose.duration_s, 9357.0, rel_tol=1e-5)

    def test_battery_usb_connected(self, device_data_payload: bytes) -> None:
        """Battery level_percent must be None when USB is connected."""
        data = parse_device_data(device_data_payload)
        assert data.battery.state.usb_connected is True
        assert data.battery.state.initialized is True
        # Critical business rule: level_percent = None when USB connected
        assert data.battery.level_percent is None

    def test_system_state_initialized(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        # 0x40000000 = only bit 30 set (initialized)
        assert data.system_state.initialized is True
        assert data.system_state.has_alarms() is False
        assert data.system_state.has_faults() is False
        assert data.system_state.is_ready() is True

    def test_measurement_id(self, device_data_payload: bytes) -> None:
        data = parse_device_data(device_data_payload)
        assert data.measurement_id == 37426
