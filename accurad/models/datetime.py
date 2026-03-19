"""Bitfield decoders for the AccuRad Date_t and Time_t packed structures.

The AccuRad PRD packs date and time into 32-bit words using C bitfields.
Python's ``struct`` module cannot decode C bitfields directly, so we unpack
a uint32 (little-endian) and extract fields with bitmasks.

Reference: protocol_reference.json -> data_types
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from accurad._constants import TIMEZONE_TABLE
from accurad.models.enums import DaylightSaving


@dataclass(frozen=True)
class AccuRadTime:
    """Decoded Time_t bitfield (4 bytes, little-endian).

    Attributes:
        hours: 0-23.
        minutes: 0-59.
        seconds: 0-59.
        milliseconds: 0-999 (13-bit field supports up to 8191).
        daylight: Daylight saving adjustment.

    """

    hours: int
    minutes: int
    seconds: int
    milliseconds: int
    daylight: DaylightSaving


@dataclass(frozen=True)
class AccuRadDate:
    """Decoded Date_t bitfield (4 bytes, little-endian).

    Attributes:
        day_of_week: 0=Sunday .. 6=Saturday (3-bit field).
        day: 1-31.
        month: 1-12.
        year: Full year (e.g. 2020).

    """

    day_of_week: int
    day: int
    month: int
    year: int


def decode_time(data: bytes, offset: int = 0) -> AccuRadTime:
    """Decode a 4-byte Time_t bitfield from *data* at *offset*.

    Bitfield layout (LSB first):
        bits  0-4:  hours        (5 bits,  mask 0x1F)
        bits  5-10: minutes      (6 bits,  mask 0x3F)
        bits 11-16: seconds      (6 bits,  mask 0x3F)
        bits 17-29: milliseconds (13 bits, mask 0x1FFF)
        bits 30-31: daylight     (2 bits,  mask 0x03)

    Args:
        data: Raw bytes containing the Time_t word.
        offset: Byte offset into *data*.

    Returns:
        Decoded time structure.

    """
    raw: int = struct.unpack_from("<I", data, offset)[0]
    return AccuRadTime(
        hours=raw & 0x1F,
        minutes=(raw >> 5) & 0x3F,
        seconds=(raw >> 11) & 0x3F,
        milliseconds=(raw >> 17) & 0x1FFF,
        daylight=DaylightSaving((raw >> 30) & 0x03),
    )


def decode_date(data: bytes, offset: int = 0) -> AccuRadDate:
    """Decode a 4-byte Date_t bitfield from *data* at *offset*.

    Bitfield layout (LSB first):
        bits  0-2:  day_of_week (3 bits,  mask 0x07)
        bits  3-7:  day         (5 bits,  mask 0x1F)
        bits  8-11: month       (4 bits,  mask 0x0F)
        bits 12-31: year        (20 bits, mask 0xFFFFF)

    Args:
        data: Raw bytes containing the Date_t word.
        offset: Byte offset into *data*.

    Returns:
        Decoded date structure.

    """
    raw: int = struct.unpack_from("<I", data, offset)[0]
    return AccuRadDate(
        day_of_week=raw & 0x07,
        day=(raw >> 3) & 0x1F,
        month=(raw >> 8) & 0x0F,
        year=(raw >> 12) & 0xFFFFF,
    )


def decode_datetime(
    data: bytes,
    offset: int = 0,
    timezone_index: int | None = None,
) -> datetime:
    """Decode an 8-byte DateTime_t (Time_t + Date_t) into a Python datetime.

    The AccuRad packs DateTime as Time_t (4 bytes) followed by Date_t (4 bytes).

    Args:
        data: Raw bytes containing the DateTime_t (8 bytes).
        offset: Byte offset into *data*.
        timezone_index: Optional timezone index (0-37) from the device.
            If provided, the returned datetime is timezone-aware.

    Returns:
        A Python datetime object (aware if timezone_index given, naive otherwise).

    """
    time = decode_time(data, offset)
    date = decode_date(data, offset + 4)

    tz = None
    if timezone_index is not None:
        tz = _timezone_from_index(timezone_index)

    return datetime(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=time.hours,
        minute=time.minutes,
        second=time.seconds,
        microsecond=time.milliseconds * 1000,
        tzinfo=tz,
    )


def _timezone_from_index(index: int) -> timezone:
    """Convert a timezone index (0-37) to a Python timezone.

    Args:
        index: AccuRad timezone index.

    Returns:
        A fixed-offset timezone.

    """
    TIMEZONE_TABLE.get(index, "")

    # Parse offset from label format "UTC+HH:MM" or "UTC-HH:MM"
    offset_hours = _TIMEZONE_OFFSETS.get(index, 0.0)
    return timezone(timedelta(hours=offset_hours))


# Pre-computed offset in hours for each timezone index
_TIMEZONE_OFFSETS: dict[int, float] = {
    0: -12.0, 1: -11.0, 2: -10.0, 3: -9.5, 4: -9.0,
    5: -8.0, 6: -7.0, 7: -6.0, 8: -5.0, 9: -4.0,
    10: -3.5, 11: -3.0, 12: -2.0, 13: -1.0, 14: 0.0,
    15: 1.0, 16: 2.0, 17: 3.0, 18: 3.5, 19: 4.0,
    20: 4.5, 21: 5.0, 22: 5.5, 23: 5.75, 24: 6.0,
    25: 6.5, 26: 7.0, 27: 8.0, 28: 8.75, 29: 9.0,
    30: 9.5, 31: 10.0, 32: 10.5, 33: 11.0, 34: 12.0,
    35: 12.75, 36: 13.0, 37: 14.0,
}
