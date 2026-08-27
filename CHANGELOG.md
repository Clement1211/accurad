# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] — 2026-03-19

Production-grade improvements: logging, error handling, retry, reconnect, thread safety, and quality-of-life features.

### Added

- **Structured logging** — Python `logging` module integrated in all modules (`accurad.client`, `accurad.connection.*`, `accurad.streaming`, `accurad.protocol.frame`). DEBUG for TX/RX hex frames and CRC, WARNING for transient errors, ERROR for unrecoverable failures.
- **Configurable retry** — `AccuRad(retries=N, retry_delay=0.5)` on factory methods. Retries only on recoverable errors (timeout, CRC mismatch). Non-recoverable errors raise immediately.
- **BLE auto-reconnect** — `connect_bluetooth(auto_reconnect=True)` transparently reconnects on connection loss (up to 3 attempts). Callbacks: `on_disconnect`, `on_reconnect`.
- **BLE automatic keep-alive** — Background timer sends heartbeat every 2s to prevent device disconnect. Enabled by default on BLE connections.
- **Per-request timeout** — `get_device_info(timeout=1.0)`, `get_measurements(timeout=2.0)` override the default.
- **Device discovery** — `AccuRad.discover_usb()` lists COM ports, `AccuRad.discover_bluetooth(timeout=10)` scans for AccuRad BLE devices (filters by `ACR*` name prefix).
- **Health check** — `device.ping(timeout=1.0)` returns True/False.
- **Wait for ready** — `device.wait_for_ready(timeout=30.0)` polls until `system_state.is_ready()`.
- **Thread safety** — `threading.Lock` on all client requests. Safe for concurrent access from streaming + logger threads.
- **`to_dict()`** on `DeviceInfo` and `DeviceData` — JSON-serializable recursive dictionaries.
- **`AccuRadConfig`** dataclass — centralized configuration (timeouts, retries, keepalive, log_frames).
- **Payload size validation** — `frame.py` validates payload size against expected sizes (65 for ID=0, 47 for ID=1) immediately after CRC check.
- **`PayloadSizeMismatchError`** exception for corrupted frames.
- **Connection state callbacks** — `on_disconnect` and `on_reconnect` on the client.

### Changed

- **Enriched exceptions** — All exceptions now have `recoverable: bool` and `suggestion: str | None` attributes. `ReadTimeoutError`, `CRCMismatchError`, `IncompleteFrameError` marked as recoverable.
- **Streaming error handling** — `stream_measurements()` and `start_logging()` accept `on_error` callback and `max_errors` parameter (stops after N consecutive errors instead of silently looping forever).
- **`start_logging()` returns logger object** — Callers can manage lifecycle directly (`logger.stop()`). `stop_logging()` still works for backward compatibility.
- **`connect_bluetooth()` default timeout** — Changed from 5.0s to 15.0s (Windows GATT discovery needs more time).
- **Version bumped** to `0.2.0`.

### Fixed

- Silent infinite error loop in `_MeasurementLogger` — errors are now logged with `exc_info=True` and counted.

---

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
- **Device data CRC**: Manual's decoded CRC value 0xA94F is a documentation error; correct value is 0x599E.
- **BLE timeout**: Default connect timeout increased from 5s to 15s (Windows GATT service discovery is slow).
- **BLE Windows**: Must scan first with `BleakScanner.find_device_by_address()` before connecting — `BleakClient(address_string)` fails silently on WinRT.

### Test results

- 33/33 unit tests passing (CRC, frame parsing, datetime bitfields, parsers, system state)
- mypy --strict: 0 errors on 20 source files
- ruff: all checks passed
- Hardware-tested: USB (COM3) and BLE (FC:0F:E7:A7:D8:9F) on Windows 11
