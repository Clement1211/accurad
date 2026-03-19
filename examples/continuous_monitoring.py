"""Continuous monitoring example — stream measurements with CSV logging.

Usage:
    python examples/continuous_monitoring.py COM3
    python examples/continuous_monitoring.py COM3 --log output.csv
"""

from __future__ import annotations

import argparse
import signal

from accurad import AccuRad
from accurad.streaming import start_logging, stop_logging, stream_measurements


def main() -> None:
    """Stream measurements and optionally log to CSV."""
    parser = argparse.ArgumentParser(description="AccuRad continuous monitoring")
    parser.add_argument("port", help="COM port (e.g. COM3, /dev/ttyUSB0)")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval (seconds)")
    parser.add_argument("--log", metavar="FILE", help="Log measurements to CSV file")
    args = parser.parse_args()

    # Graceful shutdown on Ctrl+C
    stop = False

    def on_signal(_sig: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, on_signal)

    with AccuRad.connect_usb(args.port) as device:
        # Start file logging if requested
        if args.log:
            start_logging(device, args.log, fmt="csv", interval=args.interval)
            print(f"Logging to {args.log}")

        print(f"Streaming measurements every {args.interval}s (Ctrl+C to stop)\n")
        cols = ["Dose Rate", "Count Rate", "Background", "Dose", "ID"]
        print(f"{cols[0]:>12}  {cols[1]:>12}  {cols[2]:>12}  {cols[3]:>12}  {cols[4]:>8}")
        print("-" * 65)

        try:
            for data in stream_measurements(device, interval=args.interval):
                if stop:
                    break
                print(
                    f"{data.merged.dose_rate_usv_h:>11.4f}  "
                    f"{data.merged.count_rate_cps:>11.2f}  "
                    f"{data.merged.background_dose_rate_usv_h:>11.4f}  "
                    f"{data.dose.dose_usv:>11.6f}  "
                    f"{data.measurement_id:>8}"
                )
        finally:
            if args.log:
                stop_logging()
                print(f"\nLog saved to {args.log}")
            print("Done.")


if __name__ == "__main__":
    main()
