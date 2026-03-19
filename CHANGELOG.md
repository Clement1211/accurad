# Changelog

## [0.1.0] — 2026-03-19

Initial release — fully functional, hardware-tested on AccuRad PRD (S/N 003CEE, FW 1.6.0.0).

### Features

- **USB transport** — `AccuRad.connect_usb()` via pyserial (921600 bps, auto-sync on `#!AccuRad!#` marker)
- **Bluetooth BLE transport** — `AccuRad.connect_bluetooth()` via bleak (Windows/Linux/macOS)
  - Scan-first connection (required on Windows WinRT)
  - Mandatory 1s post-connect delay
  - Background event loop thread for reliable notification handling
- **Device info** — `get_device_info()` returns manufacturer, part number, serial number, firmware version, device datetime, timezone
- **Measurements** — `get_measurements()` returns dose rate, count rate, background, accumulated dose, battery, system state (32 flags)
- **Streaming** — `stream_measurements()` generator with configurable interval
- **Logging** — `start_logging()` / `stop_logging()` to CSV or JSON lines in background thread
- **CRC16 validation** — Polynomial 0xAC5E on ID+Payload, with zero-avoidance
- **System state parsing** — `has_alarms()`, `has_faults()`, `get_active_alarms()`, `get_active_faults()`, `is_ready()`
- **Battery business rule** — `level_percent = None` when USB connected (hardware reports unreliable values)
- **Exception hierarchy** — `AccuRadError` > `ConnectionError`, `ProtocolError`, `DeviceError`, `ReadTimeoutError`

### Protocol corrections discovered during development

- **CRC scope**: Manual says "CRC computed on XXXXX" — XXXXX = ID + Payload (not just payload). Verified against manual's device info example (0x5B02).
- **Device data CRC**: Manual bytes `4F A9` decode to 0xA94F, but the manual's decoded value says "0x5B02" (copy-pasted from device info). Correct CRC for device data is **0x599E**.
- **BLE timeout**: Default connect timeout increased from 5s to 15s (Windows GATT service discovery is slow).
- **BLE Windows**: Must scan first with `BleakScanner.find_device_by_address()` before connecting — `BleakClient(address_string)` fails silently on WinRT.

### Test results

- 33/33 unit tests passing (CRC, frame parsing, datetime bitfields, parsers, system state)
- mypy --strict: 0 errors on 20 source files
- ruff: all checks passed
- Hardware-tested: USB (COM3) and BLE (FC:0F:E7:A7:D8:9F) on Windows 11
