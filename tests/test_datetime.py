"""Tests for Date_t and Time_t bitfield decoders.

Validates against the decoded examples from the manual.
"""

from __future__ import annotations

from accurad.models.datetime import AccuRadDate, AccuRadTime, decode_date, decode_time
from accurad.models.enums import DaylightSaving


class TestDecodeTime:
    """Time_t bitfield decoder tests."""

    def test_manual_example(self) -> None:
        """0x066841EE -> 14:15:08.820, daylight=0.

        Raw bytes (LE): EE 41 68 06
        """
        data = bytes.fromhex("EE416806")
        result = decode_time(data)
        assert isinstance(result, AccuRadTime)
        assert result.hours == 14
        assert result.minutes == 15
        assert result.seconds == 8
        assert result.milliseconds == 820
        assert result.daylight == DaylightSaving.NONE


class TestDecodeDate:
    """Date_t bitfield decoder tests."""

    def test_manual_example(self) -> None:
        """0x007E42C1 -> Monday, 2020-02-24.

        Raw bytes (LE): C1 42 7E 00
        """
        data = bytes.fromhex("C1427E00")
        result = decode_date(data)
        assert isinstance(result, AccuRadDate)
        assert result.day_of_week == 1  # Monday
        assert result.day == 24
        assert result.month == 2
        assert result.year == 2020
