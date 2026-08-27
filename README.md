# AccuRad PRD API

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)

Open-source Python library for communicating with the **Mirion Technologies AccuRad PRD** (Personal Radiation Detector) via USB or Bluetooth BLE.

Read-only API — retrieves device information, real-time radiation measurements, battery status, and system state. No device configuration writes.

## Features

- **USB and Bluetooth BLE** transports (pyserial / bleak)
- **Real-time measurements** — dose rate, count rate, background, accumulated dose
- **System state** — 32 alarm/fault flags with `has_alarms()`, `get_active_faults()`, `is_ready()`
- **Streaming** — `stream_measurements()` generator with configurable interval
- **File logging** — CSV or JSON lines in a background thread
- **Configurable retries** — automatic retry on transient errors (timeout, CRC)
- **BLE auto-reconnect** — transparent reconnection on connection loss
- **BLE keep-alive** — automatic heartbeat prevents device disconnect
- **Device discovery** — scan for USB ports and BLE devices
- **Thread-safe** — safe to use from multiple threads
- **Fully typed** — passes `mypy --strict`, frozen dataclasses, `to_dict()` serialization
- **Structured logging** — Python `logging` module throughout (`accurad.*` loggers)

## Installation

```bash
# USB only
pip install git+https://github.com/Clement1211/accurad.git

# With Bluetooth support
pip install "accurad[bluetooth] @ git+https://github.com/Clement1211/accurad.git"
```

## Quick Start

### USB

```python
from accurad import AccuRad

with AccuRad.connect_usb("COM3") as device:
    info = device.get_device_info()
    print(f"S/N: {info.serial_number}, FW: {info.firmware_version}")

    data = device.get_measurements()
    print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} µSv/h")
    print(f"Count rate: {data.merged.count_rate_cps:.2f} cps")

    if data.system_state.has_alarms():
        print(f"ALARMS: {data.system_state.get_active_alarms()}")
```

### Bluetooth BLE

```python
from accurad import AccuRad

# Scan for devices
devices = AccuRad.discover_bluetooth(timeout=10.0)
for d in devices:
    print(f"{d['name']} — {d['address']}")

# Connect
with AccuRad.connect_bluetooth("FC:0F:E7:A7:D8:9F") as device:
    data = device.get_measurements()
    print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} µSv/h")
```

### Continuous Monitoring

```python
from accurad import AccuRad, stream_measurements

with AccuRad.connect_usb("COM3") as device:
    for data in stream_measurements(device, interval=1.0):
        print(f"{data.merged.dose_rate_usv_h:.4f} µSv/h")
```

### File Logging

```python
from accurad import AccuRad, start_logging, stop_logging

with AccuRad.connect_usb("COM3") as device:
    start_logging(device, "measurements.csv", fmt="csv", interval=1.0)
    # ... do other work ...
    stop_logging()
```

### JSON Serialization

```python
import json
from accurad import AccuRad

with AccuRad.connect_usb("COM3") as device:
    data = device.get_measurements()
    print(json.dumps(data.to_dict(), indent=2))
```

## Advanced Usage

### Retry and Auto-Reconnect

```python
# USB with automatic retries on transient errors
device = AccuRad.connect_usb("COM3", retries=3, retry_delay=0.5)

# BLE with auto-reconnect on connection loss
device = AccuRad.connect_bluetooth(
    "FC:0F:E7:A7:D8:9F",
    retries=2,
    auto_reconnect=True,
)
```

### Connection Callbacks

```python
device = AccuRad.connect_bluetooth("FC:0F:E7:A7:D8:9F", auto_reconnect=True)
device.on_disconnect = lambda: print("Connection lost!")
device.on_reconnect = lambda: print("Reconnected!")
```

### Wait for Device Ready

```python
# Block until the device finishes its ~30s initialization
data = device.wait_for_ready(timeout=30.0)
print(f"Device ready — dose rate: {data.merged.dose_rate_usv_h:.4f} µSv/h")
```

### Health Check

```python
if device.ping():
    print("Device is responding")
```

### Error Handling

```python
from accurad import AccuRad, AccuRadError

try:
    device = AccuRad.connect_usb("COM3")
    data = device.get_measurements()
except AccuRadError as e:
    print(f"Error: {e}")
    if e.recoverable:
        print("This error is transient — retry may succeed")
    if e.suggestion:
        print(f"Hint: {e.suggestion}")
```

### Logging / Debugging

```python
import logging

# See all AccuRad library messages
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("accurad").setLevel(logging.DEBUG)
```

## API Reference

### `AccuRad` (main client)

| Method | Description |
|---|---|
| `connect_usb(port, ...)` | Connect via USB COM port |
| `connect_bluetooth(address, ...)` | Connect via BLE |
| `get_device_info(timeout=None)` | Read device info (S/N, FW, clock) |
| `get_measurements(timeout=None)` | Read current measurements |
| `disconnect()` | Close connection |
| `ping(timeout=1.0)` | Health check (True/False) |
| `wait_for_ready(timeout=30.0)` | Block until device is initialized |
| `discover_usb()` | List available USB COM ports |
| `discover_bluetooth(timeout=10.0)` | Scan for AccuRad BLE devices |

### Data Models

| Model | Key Fields |
|---|---|
| `DeviceInfo` | `manufacturer`, `serial_number`, `firmware_version`, `device_datetime` |
| `DeviceData` | `merged`, `dose`, `battery`, `system_state`, `measurement_id` |
| `MergedMeasurement` | `dose_rate_usv_h`, `count_rate_cps`, `background_dose_rate_usv_h`, `level` |
| `DoseData` | `dose_usv`, `duration_s`, `dose_datetime` |
| `BatteryData` | `level_percent` (None if USB), `state` |
| `SystemState` | `is_ready()`, `has_alarms()`, `get_active_alarms()`, `get_active_faults()` |

All models are **frozen dataclasses** (immutable) with a `to_dict()` method for JSON serialization.

### Streaming

| Function | Description |
|---|---|
| `stream_measurements(device, interval, on_error, max_errors)` | Generator yielding `DeviceData` |
| `start_logging(device, path, fmt, interval, on_error, max_errors)` | Background file logger |
| `stop_logging()` | Stop active logging session |

## Architecture

```
accurad/
├── __init__.py          # Public API exports
├── client.py            # AccuRad class (high-level interface)
├── config.py            # AccuRadConfig dataclass
├── streaming.py         # stream_measurements(), file logging
├── exceptions.py        # Exception hierarchy with recoverable/suggestion
├── _constants.py        # Protocol constants (markers, CRC, UUIDs, timeouts)
├── connection/
│   ├── base.py          # AccuRadConnection ABC
│   ├── serial.py        # USB via pyserial
│   └── bluetooth.py     # BLE via bleak (background event loop)
├── protocol/
│   ├── frame.py         # Frame parsing + CRC validation
│   ├── crc.py           # CRC16 (polynomial 0xAC5E)
│   ├── requests.py      # Fixed request byte sequences
│   └── parsers.py       # Binary payload → dataclasses
└── models/
    ├── device_info.py   # DeviceInfo
    ├── device_data.py   # DeviceData, MergedMeasurement, DoseData, BatteryData
    ├── system_state.py  # SystemState (32 flags)
    ├── datetime.py      # Date_t / Time_t bitfield decoding
    └── enums.py         # MeasurementOrigin, TimezoneIndex
```

## Requirements

- Python 3.10+
- `pyserial >= 3.5` (USB)
- `bleak >= 0.21.0` (Bluetooth, optional)

## Development

```bash
git clone https://github.com/clementMusic/accurad.git
cd accurad
pip install -e ".[dev,bluetooth]"

# Run checks
pytest                     # 33 tests
mypy --strict accurad/     # 0 errors
ruff check accurad/        # 0 errors
```

## License

[MIT](LICENSE) — Copyright 2026 Clement
