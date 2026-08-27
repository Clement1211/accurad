# Product Requirements Document (PRD)
## AccuRad PRD API — Open-Source Communication Library

| Field | Value |
|---|---|
| **Version** | 1.2 |
| **Date** | 2026-03-19 |
| **Status** | Validated (hardware-tested) |
| **Target Device** | AccuRad PRD (Mirion Technologies) |
| **Reference Document** | DOC012721EN-E, Section 10.1 — Communication Protocol |

---

## 1. Executive Summary & Objectives

### 1.1 Vision

Create a clean, well-documented, open-source Python library enabling any developer to communicate with the Mirion Technologies AccuRad PRD personal radiation detector via USB or Bluetooth. No open API currently exists for this hardware; this library fills that gap.

### 1.2 Strategic Objectives

1. **Democratize data access** — Enable researchers, radiation protection technicians, and developers to integrate AccuRad PRD measurements into their own tools (dashboards, SCADA systems, logging, custom alerts).
2. **Industrial reliability** — Implement strict binary protocol parsing with CRC16 validation, timeout management, and complete system state interpretation.
3. **Open-source & community** — Publish under MIT license on GitHub/PyPI with exemplary documentation to encourage contributions.

### 1.3 Target Use Cases

| Use Case | Description |
|---|---|
| **Real-time monitoring** | Continuous reading of measurements (dose rate, count rate, accumulated dose) with configurable polling |
| **Logging & archival** | Timestamped data recording to CSV/JSON/database |
| **System integration** | Feed a web dashboard, alert system, or IoT platform |
| **Scripting & automation** | Device health check scripts (battery, calibration, hardware faults) |
| **Research & analysis** | Raw data collection for post-mission scientific analysis |

---

## 2. Scope & Key Features

### 2.1 In Scope (v1.0)

#### 2.1.1 Transport Layer — Device Connection

| Method | Signature | Description |
|---|---|---|
| `connect_usb()` | `connect_usb(port: str, baudrate: int = 921600) -> AccuRadConnection` | Connect via USB Virtual COM Port |
| `connect_bluetooth()` | `connect_bluetooth(address: str, timeout: float = 15.0) -> AccuRadConnection` | Connect via Bluetooth BLE (UART Service) |
| `disconnect()` | `disconnect() -> None` | Clean connection teardown |
| `is_connected` | `@property -> bool` | Connection state |

#### 2.1.2 Protocol Layer — Requests and Responses

| Method | Signature | Description |
|---|---|---|
| `get_device_info()` | `get_device_info() -> DeviceInfo` | Send ID=0 sequence and parse the full response |
| `get_measurements()` | `get_measurements() -> DeviceData` | Send ID=1 sequence and parse the full response |

#### 2.1.3 Data Layer — Typed Data Models

Structures returned by the API are **immutable Python dataclasses** mapping exactly to the protocol's C structures:

```
DeviceInfo
├── manufacturer: str          # 16 bytes, zero-terminated
├── part_number: str           # 16 bytes, zero-terminated
├── serial_number: str         # 16 bytes, zero-terminated
├── firmware_number: int       # uint32
├── firmware_version: str      # "AA.BB.CC.DD"
├── datetime: datetime         # Python datetime from packed bitfields
└── timezone: TimezoneInfo     # Index + UTC label

DeviceData
├── merged: MergedMeasurement
│   ├── state: MergedState
│   │   ├── origin: MeasurementOrigin  # Enum: UNKNOWN, LOW_RANGE, HIGH_RANGE, BOTH
│   │   ├── prd_15kev_incoherence: bool
│   │   ├── overload: bool
│   │   └── initialized: bool
│   ├── dose_rate_usv_h: float         # µSv/h
│   ├── count_rate_cps: float          # counts per second
│   ├── background_dose_rate_usv_h: float
│   ├── background_count_rate_cps: float
│   └── level: float                   # 0-9 (display indicator)
├── dose: DoseData
│   ├── datetime: datetime
│   ├── dose_usv: float                # accumulated µSv since startup/reset
│   └── duration_s: float              # integration duration in seconds
├── battery: BatteryData
│   ├── state: BatteryState
│   │   ├── level_too_low: bool
│   │   ├── level_critical: bool
│   │   ├── usb_connected: bool
│   │   ├── failure: bool
│   │   └── initialized: bool
│   └── level_percent: int | None       # 0-100, or None if USB connected (unreliable)
├── system_state: SystemState          # 32 individual flags (see §2.1.4)
└── measurement_id: int                # Counter incremented every 250ms
```

#### 2.1.4 System State Parsing — Utility Methods

`SystemState` (32-bit word) exposes each flag as a boolean attribute:

| Attribute | Bit | Description |
|---|---|---|
| `counting_fault` | 0 | Counting fault on SED PRD and/or SED 15 keV |
| `temp_sensor_fault` | 1 | Temperature sensor failure |
| `temp_out_of_range` | 2 | Temperature out of operating range |
| `check_datetime` | 3 | Date/time not up to date |
| `accumulation_enabled` | 4 | Spectral accumulation enabled |
| `accumulation_in_progress` | 5 | Accumulation in progress |
| `acknowledged` | 6 | Device in acknowledged state |
| `low_alarm` | 7 | Low alarm activated |
| `high_alarm` | 8 | High alarm activated |
| `danger` | 9 | Danger alarm activated |
| `dose_alarm` | 10 | Dose alarm activated |
| `dose_danger` | 11 | Dose danger alarm activated |
| `low_power` | 12 | Low power mode |
| `search_mode` | 13 | Search mode active |
| `calibration_expired` | 15 | Calibration needs checking |
| `vbs` | 16 | VBS triggered (background variation) |
| `magnetometer_fault` | 17 | Magnetometer failure |
| `acc_gyrometer_fault` | 18 | Accelerometer/Gyroscope failure |
| `e2p_fault` | 19 | E2PROM memory fault |
| `flash_fault` | 20 | Flash memory fault |
| `audio_fault` | 21 | Audio failure |
| `ble_fault` | 22 | Bluetooth failure |
| `discreet` | 23 | Discreet mode enabled |
| `alarm_thresholds_not_consistent` | 24 | Alarm thresholds inconsistent |
| `initialized` | 30 | Initialization sequence complete |
| `remote_ctrl` | 31 | Remote control enabled |

Utility methods:

| Method | Description |
|---|---|
| `has_alarms() -> bool` | `True` if any radiological alarm is active (bits 7-11) |
| `has_faults() -> bool` | `True` if any hardware fault is detected |
| `get_active_alarms() -> list[str]` | List of active alarm names |
| `get_active_faults() -> list[str]` | List of active fault names |
| `is_ready() -> bool` | `True` if initialized and no critical faults |

#### 2.1.5 Continuous Monitoring (High Level)

| Method | Signature | Description |
|---|---|---|
| `stream_measurements()` | `stream_measurements(interval=0.5, callback=None, on_error=None, max_errors=10) -> Iterator[DeviceData]` | Continuous measurement generator with BLE keep-alive and error handling |
| `start_logging()` | `start_logging(path, fmt="csv", interval=1.0, on_error=None, max_errors=10) -> Logger` | Start background file logging |
| `stop_logging()` | `stop_logging() -> None` | Stop logging |

### 2.2 Out of Scope (v1.0)

- **Configuration writes** to the device (the protocol intentionally does not document configuration sequences to prevent corruption — see §10.1.2)
- **Graphical user interface (GUI)**
- **Support for .n42 / .xlsx files** (exported by AccuRad App, not by this API)
- **Multi-device management** (possible but not guaranteed in v1.0)

---

## 3. Architecture & Recommended Tech Stack

### 3.1 Language: Python 3.10+

**Rationale:**
- Rich ecosystem for serial and Bluetooth communication
- Massive adoption in the scientific and radiation protection community
- Native `struct` for little-endian binary parsing
- Type hints and dataclasses for a clean, self-documenting API
- Easy publication to PyPI

### 3.2 Recommended Libraries

| Dependency | Min. Version | Role |
|---|---|---|
| `pyserial` | 3.5 | USB Virtual COM Port communication |
| `bleak` | 0.21+ | Cross-platform Bluetooth Low Energy (BLE) communication |
| `struct` (stdlib) | — | Binary frame decoding (little-endian floats, uint32, bitfields) |
| `dataclasses` (stdlib) | — | Immutable data models |
| `enum` (stdlib) | — | Enums for MeasurementOrigin, TimezoneIndex, etc. |
| `logging` (stdlib) | — | Configurable structured logging |

**Development dependencies:**

| Tool | Role |
|---|---|
| `pytest` | Unit and integration tests |
| `pytest-mock` | Mocking serial/BLE ports for hardware-free tests |
| `ruff` | Linting and formatting |
| `mypy` | Static type checking |
| `mkdocs` + `mkdocstrings` | Auto-generated documentation |
| `hatch` / `setuptools` | Build and PyPI packaging |

### 3.3 Module Architecture

```
accurad/
├── __init__.py              # Public exports: AccuRad, AccuRadConfig, stream_measurements
├── client.py                # AccuRad — main high-level class
├── config.py                # AccuRadConfig centralized configuration
├── streaming.py             # stream_measurements(), continuous logging
├── exceptions.py            # Custom exception hierarchy
├── _constants.py            # Constants: START_MARKER, POLYNOM16, BLE UUIDs, timeouts
├── connection/
│   ├── base.py              # AccuRadConnection (abstract class)
│   ├── serial.py            # SerialConnection (USB COM Port via pyserial)
│   └── bluetooth.py         # BluetoothConnection (BLE via bleak)
├── protocol/
│   ├── frame.py             # Frame parsing: start marker, LEN, ID, payload, CRC
│   ├── crc.py               # CRC16 implementation (polynomial 0xAC5E)
│   ├── requests.py          # Raw request byte sequences (ID=0, ID=1)
│   └── parsers.py           # Payload decoding to dataclasses
└── models/
    ├── device_info.py       # DeviceInfo dataclass
    ├── device_data.py       # DeviceData, MergedMeasurement, DoseData, BatteryData
    ├── system_state.py      # SystemState with utility methods
    ├── datetime.py          # Date_t and Time_t bitfield parsing
    └── enums.py             # MeasurementOrigin, TimezoneIndex, etc.
```

### 3.4 Request Flow Diagram

```
Application
    │
    ▼
AccuRad.get_measurements()
    │
    ├─► _constants.py: DEVICE_DATA_REQUEST = b'\x7E\x04\x00\x11\xA7\x1E\x43\xE7'
    │
    ├─► _request() acquires thread lock, sends request, receives response (with retry)
    │
    ├─► connection.send(DEVICE_DATA_REQUEST)
    │
    ├─► connection.receive() → raw bytes
    │
    ├─► frame.py: parse_frame(raw)
    │   ├─ Verify start marker "#!AccuRad!#"
    │   ├─ Extract LEN (2 bytes LE) — LEN includes ID + Payload + CRC
    │   ├─ Extract ID (2 bytes LE)
    │   ├─ Extract payload (LEN - 4 bytes: -2 ID, -2 CRC)
    │   ├─ Extract received CRC (last 2 bytes LE)
    │   ├─ crc.py: crc16(ID + payload) == received CRC?
    │   └─ Validate payload size against expected for frame ID
    │
    ├─► parsers.py: parse_device_data(payload) → DeviceData
    │
    └─► return DeviceData
```

---

## 4. Security, Reliability & Error Handling

### 4.1 Data Integrity Validation — CRC16

Every frame's integrity is verified via CRC16 with custom polynomial `0xAC5E`.

**Algorithm (faithfully translated from the documentation's C source):**

```python
POLYNOM16 = 0xAC5E

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        if crc == 0:
            crc = 1
        for _ in range(8):
            parity = crc & 1
            crc >>= 1
            if parity:
                crc ^= POLYNOM16
    return crc
```

**Rules:**
- CRC is computed on **ID + payload** (= everything between LEN and CRC in the frame, referred to as "XXXXX" in the manual)
- If computed CRC doesn't match received CRC → raise `CRCMismatchError`
- No data is ever returned to the user if the CRC fails
- **Note:** The manual states "CRC computed on payload" which is ambiguous. Analysis of example frames proves the CRC covers ID + payload (verified: CRC(ID+Payload) = 0x5B02 for device info). The device data CRC value in the manual (0xA94F / 0x5B02) is a documentation error; the correct value is 0x599E.

### 4.2 Timeout Management

#### 4.2.1 Bluetooth Timeouts (manual specifications §10.1.3.3.3)

| Timeout | Value | Behavior |
|---|---|---|
| **Post-connect** | 1 second | After BLE connection, wait 1s before any request, otherwise communication may fail |
| **Keep-alive** | 2.5 seconds max | AccuRad must receive a valid message at least every 2.5s, otherwise it enters discoverable mode (disconnects) |
| **Discoverable** | 60 seconds | After connection loss or NFC scan, device is visible for 60s then turns off Bluetooth (except in "opened" mode) |

**Implementation:**
- In `stream_measurements()` mode, an automatic heartbeat (ID=1 request) is sent every 2 seconds maximum to maintain the BLE connection
- A background timer thread sends keep-alive if no request has been sent within the interval
- After BLE connect, `await asyncio.sleep(1.0)` is inserted automatically

#### 4.2.2 General Timeouts

| Parameter | Default | Configurable |
|---|---|---|
| `read_timeout` | 3.0s | Yes |
| `write_timeout` | 1.0s | Yes |
| `connect_timeout` | 15.0s (BLE) / 2.0s (USB) | Yes |

### 4.3 Exception Hierarchy

```
AccuRadError (base) — recoverable, suggestion attributes
├── ConnectionError          (recoverable=False)
│   ├── USBConnectionError
│   ├── BluetoothConnectionError
│   └── ConnectionTimeoutError  (recoverable=True)
├── ProtocolError            (recoverable=False)
│   ├── InvalidFrameError
│   ├── CRCMismatchError     (recoverable=True)
│   ├── UnexpectedFrameIDError
│   ├── IncompleteFrameError (recoverable=True)
│   └── PayloadSizeMismatchError
├── DeviceError
│   ├── DeviceNotInitializedError (recoverable=True)
│   └── DeviceNotReadyError
└── ReadTimeoutError         (recoverable=True)
```

### 4.4 Hardware State Parsing

The API **does not hide any information** but provides interpretation levels:

**Level 1 — Raw:** Direct access to each boolean flag via `system_state.low_alarm`, etc.

**Level 2 — Categorized:**
```python
# Radiological alarms
system_state.has_alarms()        # low_alarm OR high_alarm OR danger OR dose_alarm OR dose_danger
system_state.get_active_alarms() # ["low_alarm", "danger"]

# Hardware faults
system_state.has_faults()        # counting_fault OR temp_sensor_fault OR ... OR ble_fault
system_state.get_active_faults() # ["temp_out_of_range", "flash_fault"]
```

**Level 3 — Operational:**
```python
system_state.is_ready()          # initialized AND NOT has_faults()
```

### 4.5 Connection Robustness

- **Automatic reconnection**: Optional, disabled by default. When enabled, the API attempts reconnection after BLE connection loss (within the 60s discoverable window). Max 3 reconnection attempts.
- **Buffer flush**: On every new connection, the receive buffer is flushed to avoid parsing residual data
- **Start marker validation**: Every response is scanned for the `#!AccuRad!#` pattern (11 bytes: `0x23 0x21 0x41 0x63 0x63 0x75 0x52 0x61 0x64 0x21 0x23`). Bytes before this marker are discarded (synchronization)
- **Configurable retries**: Automatic retry on recoverable errors (timeout, CRC mismatch). Non-recoverable errors raise immediately.
- **Thread safety**: All requests are serialized via `threading.Lock`

---

## 5. Dependencies and System Requirements

### 5.1 For API Users

| Prerequisite | Detail |
|---|---|
| **Python** | 3.10 or higher |
| **OS** | Windows 10+, Linux (Ubuntu 20.04+), macOS 12+ |
| **Hardware** | AccuRad PRD with firmware V1.1+ |
| **USB** | USB-C cable, COM port driver installed (automatic on most OS) |
| **Bluetooth** | BLE 4.0+ adapter (built-in or USB). AccuRad must have Bluetooth enabled and be in discoverable or "opened" mode |

### 5.2 Installation

```bash
# Standard install (USB only)
pip install accurad

# With Bluetooth support
pip install accurad[bluetooth]

# Developer install
pip install accurad[dev]
```

### 5.3 Bluetooth Compatibility Matrix

| OS | BLE Backend | Notes |
|---|---|---|
| Windows 10+ | WinRT (via bleak) | Works natively. Scan-first required (see N7). |
| Linux | BlueZ 5.43+ (via bleak) | `sudo` may be required for BLE scanning |
| macOS 12+ | CoreBluetooth (via bleak) | Bluetooth permissions required in System Preferences |

### 5.4 Minimal Example

```python
from accurad import AccuRad

# USB — simplest
device = AccuRad.connect_usb("COM3")       # Windows
device = AccuRad.connect_usb("/dev/ttyUSB0")  # Linux
device = AccuRad.connect_usb("/dev/cu.usbmodem1234")  # macOS

# Bluetooth
device = AccuRad.connect_bluetooth("XX:XX:XX:XX:XX:XX")

# Read
info = device.get_device_info()
print(f"S/N: {info.serial_number}, FW: {info.firmware_version}")

data = device.get_measurements()
print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} µSv/h")
print(f"Battery: {data.battery.level_percent}%")

if data.system_state.has_alarms():
    print(f"ACTIVE ALARMS: {data.system_state.get_active_alarms()}")

device.disconnect()
```

---

## 6. Implementation Plan (Milestones)

### Milestone 0 — Project Setup ✅

- [x] Git repository, folder structure, `pyproject.toml`, `ruff`, `mypy`, `pytest`
- [x] GitHub Actions CI (multi-OS, multi-Python)
- [x] `README.md`, `.gitignore`, `CLAUDE.md`

### Milestone 1 — Raw Protocol Layer ✅

- [x] `_constants.py`, `crc.py`, `frame.py`, `models/datetime.py`, `models/enums.py`, `exceptions.py`
- [x] CRC16 validated against manual frames (0x5B02 device info, 0x599E device data)
- [x] **Discovery:** CRC covers ID + Payload (not just payload). Manual documentation error corrected.
- [x] 33 unit tests passing

### Milestone 2 — Payload Parsers ✅

- [x] All models: `DeviceInfo`, `DeviceData`, `MergedMeasurement`, `DoseData`, `BatteryData`, `SystemState`
- [x] Parsers validated field-by-field against manual examples
- [x] Battery USB business rule implemented

### Milestone 3 — USB Transport ✅ (hardware-tested)

- [x] `SerialConnection` with start marker synchronization, timeouts, buffer flush
- [x] `AccuRad` client with `connect_usb()`, `get_device_info()`, `get_measurements()`
- [x] Tested on real AccuRad (S/N 003CEE, FW 1.6.0.0) — USB COM3

### Milestone 4 — Bluetooth Transport ✅ (hardware-tested)

- [x] `BluetoothConnection` via bleak with threaded event loop (Windows WinRT fix)
- [x] Mandatory scan-first (Windows doesn't find device by address alone)
- [x] Post-connect 1s delay, keep-alive, 15s timeout (GATT discovery slow on Windows)
- [x] Tested on real AccuRad via BLE (FC:0F:E7:A7:D8:9F)

### Milestone 5 — Streaming & High Level ✅ (hardware-tested)

- [x] `stream_measurements()` — sync generator with natural keep-alive
- [x] `start_logging()` / `stop_logging()` — CSV and JSON lines, background thread
- [x] Context manager on `AccuRad` and `AccuRadConnection`
- [x] Tested USB + BLE streaming, CSV logging verified

### Milestone 6 — Production Hardening ✅ (v0.2.0)

- [x] Structured logging (`logging` module) in all modules
- [x] Error handling: `on_error` callback + `max_errors` on streaming
- [x] Enriched exceptions with `recoverable` and `suggestion` attributes
- [x] Configurable retry with `retries` and `retry_delay` parameters
- [x] BLE auto-reconnect with `auto_reconnect=True`
- [x] BLE automatic keep-alive background timer
- [x] `AccuRadConfig` centralized configuration dataclass
- [x] Device discovery: `discover_usb()`, `discover_bluetooth()`
- [x] Per-request timeout override
- [x] Thread safety with `threading.Lock`
- [x] `ping()` health check, `wait_for_ready()` convenience method
- [x] `to_dict()` JSON serialization on all models
- [x] Payload size validation in frame parser
- [x] Connection state callbacks (`on_disconnect`, `on_reconnect`)

### Milestone 7 — Documentation & Packaging (in progress)

- [x] Google-style docstrings on all public methods
- [x] 4 examples: `basic_usb.py`, `basic_bluetooth.py`, `continuous_monitoring.py`, `alarm_watcher.py`
- [x] `demo/live_dashboard.py` — real-time terminal dashboard
- [ ] MkDocs documentation
- [ ] PyPI publication
- [ ] `CONTRIBUTING.md`

---

## Appendix 0 — Critical Implementation Notes (READ FIRST)

> These are the most likely pitfalls during implementation. Every developer must read this section before writing any code.

### N1. LEN Field Includes ID (CORRECTED in v1.1)

The manual text says "length of XXXXX + CRC" which is ambiguous. **Analysis of example frames proves that LEN = ID(2) + Payload(N) + CRC(2) = N + 4.**

| Frame | Actual Payload | Expected LEN | LEN in Manual |
|---|---|---|---|
| Device Info (ID=0) | 65 bytes | 65 + 2 + 2 = 69 | 0x0045 = 69 ✓ |
| Device Data (ID=1) | 47 bytes | 47 + 2 + 2 = 51 | 0x0033 = 51 ✓ |

**Code impact:** `payload_size = LEN - 4` (not LEN - 2). Getting this wrong = desynchronization + systematic CRC failure.

### N2. C Bitfields ≠ Python struct

Python `struct` does not support bit fields. For `Time_t` and `Date_t`:
1. `struct.unpack("<I", data)` → uint32 little-endian
2. Bitmasks to isolate each field

Verified example: `0x066841EE` → Hours=14, Minutes=15, Seconds=8, Ms=820, Daylight=0

### N3. Battery level_percent Unreliable on USB

When `BatteryState.usb_connected == True`, the hardware reports a `level_percent` that does not reflect the actual charge. The parser must force this value to `None` to prevent end users from making decisions based on erroneous data.

### N4. Bluetooth: Mandatory 1s Post-Connect Delay

After `BleakClient.connect()`, you **must** wait a full 1 second before sending the first request. Without this delay, communication fails intermittently and non-reproducibly — making it a particularly difficult bug to diagnose.

### N5. Bluetooth: 2.5s Keep-Alive Timeout

The AccuRad disconnects the BLE connection if no valid message is received within 2.5s. The heartbeat timer must be integrated in the Bluetooth transport layer, not in user code.

### N6. CRC Computed on ID + Payload (CORRECTED in v1.2)

The manual says "CRC computed on XXXXX" where XXXXX represents everything between LEN and CRC in the frame, i.e., **ID + Payload**. The initial implementation assumed "payload only" — that was wrong. Verified: `CRC16(ID + Payload) = 0x5B02` matches exactly the manual's device info frame. The device data CRC value in the manual (0xA94F in bytes, decoded as 0x5B02) is a copy-paste error; the correct value is **0x599E**.

### N7. Bluetooth Windows: Scan-First Required (added in v1.2)

On Windows (WinRT backend), `BleakClient(address)` cannot find the device by MAC address alone. You must first scan with `BleakScanner.find_device_by_address()` then pass the resulting `BLEDevice` to `BleakClient`. Additionally, the default connection timeout must be **15s** (not 5s) because GATT discovery is slow on Windows.

---

## Appendix A — Protocol Quick Reference

### Request Sequences (send as-is)

| Request | ID | Hex Sequence |
|---|---|---|
| Device Information | 0 | `7E 04 00 10 A7 07 46 E7` |
| Device Measurements | 1 | `7E 04 00 11 A7 1E 43 E7` |

### Response Frame Format

```
┌─────────────┬──────────┬──────────┬─────────────────┬──────────┐
│ #!AccuRad!# │  LEN     │   ID     │    Payload      │  CRC16   │
│  11 bytes   │ 2 bytes  │ 2 bytes  │   N bytes       │ 2 bytes  │
│  (ASCII)    │  (LE)    │  (LE)    │                 │  (LE)    │
└─────────────┴──────────┴──────────┴─────────────────┴──────────┘
                          ◄──────── LEN = N + 4 ────────►
```

> **WARNING — LEN Calculation:** The LEN field includes ID (2 bytes) + Payload (N bytes) + CRC (2 bytes), i.e., **LEN = N + 4**. It is NOT Payload + CRC only.
>
> **Proof from manual frames:**
> - Device Info (ID=0): Payload = 65 bytes → LEN = 65 + 2 + 2 = **69 = 0x0045** ✓
> - Device Data (ID=1): Payload = 47 bytes → LEN = 47 + 2 + 2 = **51 = 0x0033** ✓

- **LEN** = ID (2 bytes) + Payload (N bytes) + CRC (2 bytes) = **N + 4**
- **Payload size** = LEN - 4 (to extract raw payload from LEN)
- **CRC16** computed on **ID + payload** (polynomial 0xAC5E) — see Appendix 0, N6
- Byte order: little-endian for multi-byte words
- Bit order: MSB first within each byte

### Bluetooth BLE UUIDs

| Characteristic | UUID |
|---|---|
| UART Service | `49535343-FE7D-4AE5-8FA9-9FAFD205E455` |
| UART TX (Notify/Write) | `49535343-1E4D-4BD9-BA61-23C647249616` |

---

## Appendix B — Payload Sizes

| Frame ID | Payload (N) | LEN = N + 4 | Total Frame Size (11 + 2 + LEN) |
|---|---|---|---|
| 0 (Device Info) | 65 bytes (16+16+16+4+4+8+1) | 69 (0x0045) | 11 + 2 + 69 = **82 bytes** |
| 1 (Device Data) | 47 bytes (21+16+2+4+4) | 51 (0x0033) | 11 + 2 + 51 = **64 bytes** |

> **Complete frame breakdown:** Start Marker (11) + LEN (2) + ID (2) + Payload (N) + CRC (2).
> The LEN field covers bytes after itself: ID (2) + Payload (N) + CRC (2) = N + 4.

### Payload Detail ID=0 (Device Information)

| Offset | Size | Field |
|---|---|---|
| 0 | 16 | Manufacturer (string, zero-terminated) |
| 16 | 16 | Part Number (string, zero-terminated) |
| 32 | 16 | Serial Number (string, zero-terminated) |
| 48 | 4 | Firmware Number (uint32 LE) |
| 52 | 4 | Firmware Version (uint32 LE → AA.BB.CC.DD) |
| 56 | 8 | DateTime (Time_t 4B + Date_t 4B) |
| 64 | 1 | Timezone Index (uint8) |

### Payload Detail ID=1 (Device Data)

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | Merged State (uint8, bitfield) |
| 1 | 4 | Dose Rate µSv/h (float32 LE) |
| 5 | 4 | Count Rate cps (float32 LE) |
| 9 | 4 | Background Dose Rate µSv/h (float32 LE) |
| 13 | 4 | Background Count Rate cps (float32 LE) |
| 17 | 4 | Level 0-9 (float32 LE) |
| 21 | 4 | Dose Time (Time_t, uint32 LE bitfield) |
| 25 | 4 | Dose Date (Date_t, uint32 LE bitfield) |
| 29 | 4 | Dose µSv (float32 LE) |
| 33 | 4 | Dose Duration s (float32 LE) |
| 37 | 1 | Battery State (uint8, bitfield) |
| 38 | 1 | Battery Level % (uint8) |
| 39 | 4 | System State (uint32 LE, bitfield) |
| 43 | 4 | Measurement ID (uint32 LE) |

---

*End of PRD — This document is the complete reference for AccuRad PRD API development.*
