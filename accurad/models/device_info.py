"""DeviceInfo model — response to frame ID=0 (Device Information).

Reference: protocol_reference.json -> payloads -> id_0_device_info
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class DeviceInfo:
    """Parsed device information from an ID=0 response.

    Attributes:
        manufacturer: Device manufacturer string (e.g. "MANUFACTURER").
        part_number: Part number string (e.g. "NOM004537-C").
        serial_number: Serial number string (e.g. "000024").
        firmware_number: Raw firmware build number (e.g. 1547).
        firmware_version: Human-readable version string "AA.BB.CC.DD".
        device_datetime: Device's internal clock as a Python datetime.
        timezone_index: Raw timezone index (0-37).
        timezone_label: Human-readable timezone label (e.g. "UTC+01:00 (Paris)").

    """

    manufacturer: str
    part_number: str
    serial_number: str
    firmware_number: int
    firmware_version: str
    device_datetime: datetime
    timezone_index: int
    timezone_label: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        d = asdict(self)
        d["device_datetime"] = self.device_datetime.isoformat()
        return d
