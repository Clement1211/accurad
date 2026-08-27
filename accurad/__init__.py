"""AccuRad PRD API — Python library for the Mirion AccuRad radiation detector.

Quick start:
    >>> from accurad import AccuRad
    >>> with AccuRad.connect_usb("COM3") as device:
    ...     info = device.get_device_info()
    ...     data = device.get_measurements()
"""

from __future__ import annotations

from accurad.client import AccuRad
from accurad.config import AccuRadConfig
from accurad.exceptions import AccuRadError
from accurad.streaming import start_logging, stop_logging, stream_measurements

__all__ = [
    "AccuRad",
    "AccuRadConfig",
    "AccuRadError",
    "start_logging",
    "stop_logging",
    "stream_measurements",
]

__version__ = "0.2.0"
