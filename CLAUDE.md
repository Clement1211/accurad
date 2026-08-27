# AccuRad PRD API — Claude Code Guide

## Project Overview

Open-source Python library to communicate with the Mirion Technologies AccuRad PRD (Personal Radiation Detector) via USB or Bluetooth BLE. Read-only API — no device configuration writes.

## Authoritative References

- **PRD (requirements):** `PRD.md` — v1.1, contains all specs, frame formats, and implementation notes
- **Protocol constants:** `protocol_reference.json` — extracted from manual, use this instead of re-reading the PDF
- **Original manual:** `DOC012721EN-E AccuRad user manual English (1).pdf` — Section 10.1 only

## Target Architecture

```
accurad/                      # Main package
├── __init__.py               # Public API: AccuRad, connect_usb, connect_bluetooth
├── _constants.py             # START_MARKER, POLYNOM16, request sequences, BLE UUIDs
├── exceptions.py             # AccuRadError hierarchy
├── client.py                 # AccuRad class — high-level interface
├── streaming.py              # stream_measurements(), start_logging()
├── connection/
│   ├── base.py               # AccuRadConnection ABC
│   ├── serial.py             # USB COM port via pyserial
│   └── bluetooth.py          # BLE via bleak (UART service)
├── protocol/
│   ├── frame.py              # Frame parsing: marker/LEN/ID/payload/CRC validation
│   ├── crc.py                # CRC16 (polynomial 0xAC5E)
│   ├── requests.py           # Raw request byte sequences (ID=0, ID=1)
│   └── parsers.py            # Binary payload → Python dataclasses
└── models/
    ├── device_info.py         # DeviceInfo dataclass
    ├── device_data.py         # DeviceData, MergedMeasurement, DoseData, BatteryData
    ├── system_state.py        # SystemState (32 flags + utility methods)
    ├── datetime.py            # Bitfield decoding for Date_t / Time_t
    └── enums.py               # MeasurementOrigin, TimezoneIndex
```

## Critical Implementation Rules

1. **LEN = ID(2) + Payload(N) + CRC(2) = N + 4** — NOT N + 2. See PRD.md Appendix 0, N1.
2. **Bitfields:** Use `struct.unpack("<I")` then bitmask extraction. Never try struct for C bitfields.
3. **Battery:** Force `level_percent = None` when `usb_connected == True`.
4. **BLE post-connect:** Always wait 1.0s after BLE connect before first request. Non-negotiable.
5. **BLE keep-alive:** Heartbeat every 2.0s max (device disconnects at 2.5s silence).
6. **Request sequences are FIXED:** Never modify `7E 04 00 10 A7 07 46 E7` (ID=0) or `7E 04 00 11 A7 1E 43 E7` (ID=1).
7. **CRC on ID + payload** — "XXXXX" in the manual = everything between LEN and CRC. NOT on start marker or LEN. (Verified: CRC(ID+Payload) matches device info example. Manual's device data CRC value 0xA94F is a doc error; correct value is 0x599E.)

## Code Conventions

- **Language:** Python 3.10+
- **Type hints:** Mandatory on all public methods. Use `from __future__ import annotations`.
- **Models:** Use `@dataclass(frozen=True)` for immutability.
- **Docstrings:** Google style.
- **Linter:** `ruff` — config in `pyproject.toml`.
- **Types:** `mypy --strict`.
- **Tests:** `pytest`. Test data = hex dumps from manual pages 115-119.
- **Dependencies:** `pyserial` (USB), `bleak` (BLE optional extra).

## Workflow

- Before implementing any parser, verify against the manual's hex examples in `protocol_reference.json`.
- Run `pytest` after every change.
- Never commit code that breaks `mypy --strict`.
