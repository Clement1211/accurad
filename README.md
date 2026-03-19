# AccuRad PRD API

Python library for communicating with the Mirion Technologies AccuRad PRD radiation detector via USB or Bluetooth BLE.

## Installation

```bash
# USB only
pip install accurad

# With Bluetooth support
pip install accurad[bluetooth]
```

## Quick Start

```python
from accurad import AccuRad

with AccuRad.connect_usb("COM3") as device:
    info = device.get_device_info()
    print(f"S/N: {info.serial_number}, FW: {info.firmware_version}")

    data = device.get_measurements()
    print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} uSv/h")

    if data.system_state.has_alarms():
        print(f"ALARMS: {data.system_state.get_active_alarms()}")
```

## Status

Under active development. See [PRD.md](PRD.md) for the full roadmap.

## License

MIT
