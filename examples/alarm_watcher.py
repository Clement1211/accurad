"""Alarm watcher — monitor device for alarm and fault conditions.

Usage:
    python examples/alarm_watcher.py COM3
"""

from __future__ import annotations

import sys
import time

from accurad import AccuRad
from accurad.streaming import stream_measurements


def main() -> None:
    """Watch for alarms and faults, print alerts when they change."""
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"

    with AccuRad.connect_usb(port) as device:
        print(f"Watching alarms on {port} (Ctrl+C to stop)\n")

        prev_alarms: list[str] = []
        prev_faults: list[str] = []

        try:
            for data in stream_measurements(device, interval=1.0):
                alarms = data.system_state.get_active_alarms()
                faults = data.system_state.get_active_faults()

                now = time.strftime("%H:%M:%S")

                # Report new alarms
                new_alarms = [a for a in alarms if a not in prev_alarms]
                cleared_alarms = [a for a in prev_alarms if a not in alarms]

                for alarm in new_alarms:
                    rate = data.merged.dose_rate_usv_h
                    print(f"[{now}] ALARM ON:  {alarm}  ({rate:.4f} uSv/h)")
                for alarm in cleared_alarms:
                    print(f"[{now}] ALARM OFF: {alarm}")

                # Report new faults
                new_faults = [f for f in faults if f not in prev_faults]
                cleared_faults = [f for f in prev_faults if f not in faults]

                for fault in new_faults:
                    print(f"[{now}] FAULT ON:  {fault}")
                for fault in cleared_faults:
                    print(f"[{now}] FAULT OFF: {fault}")

                prev_alarms = alarms
                prev_faults = faults

        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
