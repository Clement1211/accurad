"""Basic USB example — read device info and measurements.

Usage:
    python examples/basic_usb.py COM3
"""

from __future__ import annotations

import sys

from accurad import AccuRad


def main() -> None:
    """Connect to AccuRad via USB and print device info + measurements."""
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"

    with AccuRad.connect_usb(port) as device:
        # Read device info
        info = device.get_device_info()
        print(f"Manufacturer:     {info.manufacturer}")
        print(f"Part Number:      {info.part_number}")
        print(f"Serial Number:    {info.serial_number}")
        print(f"Firmware:         {info.firmware_version} (build {info.firmware_number})")
        print(f"Device Time:      {info.device_datetime}")
        print(f"Timezone:         {info.timezone_label}")
        print()

        # Read measurements
        data = device.get_measurements()
        print(f"Dose Rate:        {data.merged.dose_rate_usv_h:.4f} uSv/h")
        print(f"Count Rate:       {data.merged.count_rate_cps:.2f} cps")
        print(f"Background:       {data.merged.background_dose_rate_usv_h:.4f} uSv/h")
        print(f"Accumulated Dose: {data.dose.dose_usv:.6f} uSv")
        print(f"Dose Duration:    {data.dose.duration_s:.0f} s")
        print()

        # Battery
        if data.battery.level_percent is not None:
            print(f"Battery:          {data.battery.level_percent}%")
        else:
            print("Battery:          N/A (USB powered)")

        # System state
        if data.system_state.has_alarms():
            print(f"ALARMS:           {data.system_state.get_active_alarms()}")
        if data.system_state.has_faults():
            print(f"FAULTS:           {data.system_state.get_active_faults()}")
        if data.system_state.is_ready():
            print("Status:           READY")


if __name__ == "__main__":
    main()
