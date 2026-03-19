"""DeviceData model — response to frame ID=1 (Device Measurements).

Reference: protocol_reference.json -> payloads -> id_1_device_data
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from accurad.models.enums import MeasurementOrigin
    from accurad.models.system_state import SystemState


@dataclass(frozen=True)
class MergedState:
    """Decoded merged_state byte (8-bit bitfield).

    Attributes:
        origin: Which detector(s) contributed to the measurement.
        prd_15kev_incoherence: Low/high range measurements are inconsistent.
        overload: Detector is in overload condition.
        initialized: Measurement subsystem has initialized.

    """

    origin: MeasurementOrigin
    prd_15kev_incoherence: bool
    overload: bool
    initialized: bool


@dataclass(frozen=True)
class MergedMeasurement:
    """Merged radiation measurement data.

    Attributes:
        state: Measurement state flags and origin.
        dose_rate_usv_h: Current dose rate in microsieverts per hour.
        count_rate_cps: Current count rate in counts per second.
        background_dose_rate_usv_h: Background dose rate in uSv/h.
        background_count_rate_cps: Background count rate in cps.
        level: Display level indicator (0.0 - 9.0).

    """

    state: MergedState
    dose_rate_usv_h: float
    count_rate_cps: float
    background_dose_rate_usv_h: float
    background_count_rate_cps: float
    level: float


@dataclass(frozen=True)
class DoseData:
    """Accumulated dose information.

    Attributes:
        dose_datetime: Timestamp of the dose measurement.
        dose_usv: Accumulated dose in microsieverts since startup/reset.
        duration_s: Integration duration in seconds.

    """

    dose_datetime: datetime
    dose_usv: float
    duration_s: float


@dataclass(frozen=True)
class BatteryState:
    """Decoded battery_state byte (8-bit bitfield).

    Attributes:
        level_too_low: Battery level is too low for normal operation.
        level_critical: Battery level is critically low.
        usb_connected: Device is connected via USB (battery % unreliable).
        failure: Battery hardware failure detected.
        initialized: Battery subsystem has initialized.

    """

    level_too_low: bool
    level_critical: bool
    usb_connected: bool
    failure: bool
    initialized: bool


@dataclass(frozen=True)
class BatteryData:
    """Battery information.

    Attributes:
        state: Battery state flags.
        level_percent: Battery charge percentage (0-100), or None if USB
            connected (hardware reports unreliable values when charging).

    """

    state: BatteryState
    level_percent: int | None


@dataclass(frozen=True)
class DeviceData:
    """Parsed device measurement data from an ID=1 response.

    This is the main data structure returned by ``get_measurements()``.

    Attributes:
        merged: Current radiation measurements and detector state.
        dose: Accumulated dose data with timestamp.
        battery: Battery status and charge level.
        system_state: 32-bit system state with alarm/fault flags.
        measurement_id: Monotonically increasing counter (incremented every 250ms).

    """

    merged: MergedMeasurement
    dose: DoseData
    battery: BatteryData
    system_state: SystemState
    measurement_id: int
