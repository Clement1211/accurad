"""Enumerations for AccuRad PRD protocol values."""

from __future__ import annotations

from enum import IntEnum


class MeasurementOrigin(IntEnum):
    """Origin of the merged measurement (bits 0-1 of merged_state byte).

    Indicates which detector(s) contributed to the current measurement.
    """

    UNKNOWN = 0
    LOW_RANGE = 1    # SED PRD / CsI scintillator
    HIGH_RANGE = 2   # SED 15 keV / Pin diode
    BOTH = 3         # Both detectors contributing


class DaylightSaving(IntEnum):
    """Daylight saving time adjustment (bits 30-31 of Time_t).

    Applied to the base UTC offset indicated by the timezone index.
    """

    NONE = 0
    ADD_ONE_HOUR = 1
    SUBTRACT_ONE_HOUR = 2
