#!/usr/bin/env python3
"""AccuRad Live Dashboard — standalone demo for integrators.

Shows real-time radiation data from the AccuRad PRD in a terminal UI.
This is NOT part of the accurad library — just a demo of what the API can do.

Usage:
    python demo/live_dashboard.py              # USB auto-detect
    python demo/live_dashboard.py COM3         # USB specific port
    python demo/live_dashboard.py --ble XX:XX:XX:XX:XX:XX  # Bluetooth
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

# ---- This is all an integrator needs ----
from accurad import AccuRad
from accurad.streaming import stream_measurements

# ------------------------------------------

STOP = False


def on_signal(_sig: int, _frame: object) -> None:
    global STOP  # noqa: PLW0603
    STOP = True


signal.signal(signal.SIGINT, on_signal)


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def bar(value: float, max_val: float, width: int = 30) -> str:
    """Simple ASCII progress bar."""
    ratio = min(value / max_val, 1.0) if max_val > 0 else 0.0
    filled = int(ratio * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"


def dose_rate_color_label(rate: float) -> str:
    """Return a text severity label based on dose rate."""
    if rate < 0.2:
        return "NORMAL"
    if rate < 1.0:
        return "ELEVATED"
    if rate < 10.0:
        return "HIGH"
    return "DANGER"


def main() -> None:
    parser = argparse.ArgumentParser(description="AccuRad Live Dashboard")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("port", nargs="?", help="USB COM port (e.g. COM3)")
    group.add_argument("--ble", metavar="ADDR", help="BLE MAC address")
    parser.add_argument(
        "--interval", type=float, default=0.5, help="Refresh rate (seconds)"
    )
    args = parser.parse_args()

    # Connect
    if args.ble:
        print(f"Connecting via Bluetooth to {args.ble}...")
        device = AccuRad.connect_bluetooth(args.ble)
        transport = f"BLE ({args.ble})"
    else:
        port = args.port or auto_detect_port()
        print(f"Connecting via USB to {port}...")
        device = AccuRad.connect_usb(port)
        transport = f"USB ({port})"

    # Read device info once
    info = device.get_device_info()

    sample_count = 0
    start_time = time.monotonic()

    try:
        for data in stream_measurements(device, interval=args.interval):
            if STOP:
                break

            sample_count += 1
            elapsed = time.monotonic() - start_time

            clear()

            # Header
            print("╔══════════════════════════════════════════════════════╗")
            print("║           AccuRad PRD — Live Dashboard              ║")
            print("╚══════════════════════════════════════════════════════╝")
            print()

            # Device info
            print(f"  Device:      {info.part_number}  (S/N {info.serial_number})")
            print(f"  Firmware:    {info.firmware_version}")
            print(f"  Transport:   {transport}")
            print(f"  Timezone:    {info.timezone_label}")
            print()

            # Radiation
            rate = data.merged.dose_rate_usv_h
            severity = dose_rate_color_label(rate)
            print("  ── Radiation ────────────────────────────────────────")
            print(f"  Dose Rate:     {rate:>10.4f} uSv/h    [{severity}]")
            print(f"                 {bar(rate, 0.5)}")
            print(f"  Count Rate:    {data.merged.count_rate_cps:>10.2f} cps")
            print(f"  Background:    {data.merged.background_dose_rate_usv_h:>10.4f} uSv/h")
            print(f"  Bg Count Rate: {data.merged.background_count_rate_cps:>10.2f} cps")
            print(f"  Display Level: {data.merged.level:>10.1f} / 9.0")
            print()

            # Dose accumulation
            print("  ── Accumulated Dose ─────────────────────────────────")
            device_dose = data.dose.dose_usv
            dur = data.dose.duration_s
            h, m, s = int(dur // 3600), int((dur % 3600) // 60), int(dur % 60)
            # Device may report 0 for very small doses; show estimated
            estimated = rate * (dur / 3600.0) if dur > 0 else 0.0
            if device_dose > 0:
                print(f"  Total Dose:    {device_dose:>10.6f} uSv")
            else:
                print(f"  Total Dose:    {device_dose:>10.6f} uSv  (est. {estimated:.6f})")
            print(f"  Duration:      {h:02d}:{m:02d}:{s:02d}")
            print()

            # Battery
            print("  ── Battery ──────────────────────────────────────────")
            bat = data.battery
            if bat.level_percent is not None:
                pct = bat.level_percent
                print(f"  Level:         {pct:>3d}%  {bar(pct, 100, 20)}")
            else:
                print("  Level:         USB powered (charging)")
            flags = []
            if bat.state.level_too_low:
                flags.append("LOW")
            if bat.state.level_critical:
                flags.append("CRITICAL")
            if bat.state.failure:
                flags.append("FAILURE")
            if flags:
                print(f"  Warnings:      {', '.join(flags)}")
            print()

            # System state
            print("  ── System State ─────────────────────────────────────")
            ss = data.system_state
            status = "READY" if ss.is_ready() else "NOT READY"
            print(f"  Status:        {status}")
            alarms = ss.get_active_alarms()
            faults = ss.get_active_faults()
            if alarms:
                print(f"  Alarms:        {', '.join(alarms)}")
            else:
                print("  Alarms:        None")
            if faults:
                print(f"  Faults:        {', '.join(faults)}")
            else:
                print("  Faults:        None")
            print()

            # Detector info
            origin = data.merged.state.origin.name
            print("  ── Detector ─────────────────────────────────────────")
            print(f"  Origin:        {origin}")
            print(f"  Overload:      {'YES' if data.merged.state.overload else 'No'}")
            print(f"  Incoherence:   {'YES' if data.merged.state.prd_15kev_incoherence else 'No'}")
            print()

            # Footer
            print(f"  Measurement ID: {data.measurement_id}    "
                  f"Samples: {sample_count}    "
                  f"Uptime: {elapsed:.0f}s")
            print()
            print("  Press Ctrl+C to stop")

    finally:
        device.disconnect()
        print("\nDisconnected.")


def auto_detect_port() -> str:
    """Try to auto-detect the AccuRad USB COM port."""
    try:
        from serial.tools.list_ports import comports

        ports = list(comports())
        if len(ports) == 1:
            return ports[0].device
        for p in ports:
            desc = (p.description or "").lower()
            if "accurad" in desc or "acr" in desc or "stm" in desc:
                return p.device
        if ports:
            print("Available COM ports:")
            for p in ports:
                print(f"  {p.device}: {p.description}")
            return ports[0].device
    except ImportError:
        pass
    print("No COM port detected. Specify one: python demo/live_dashboard.py COM3")
    sys.exit(1)


if __name__ == "__main__":
    main()
