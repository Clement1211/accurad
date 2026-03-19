# AccuRad PRD API — Developer Guide

## Quick Reference

| Document | Purpose |
|---|---|
| `PRD.md` | Requirements, architecture, milestones — the "what" and "why" |
| `CLAUDE.md` | AI assistant instructions — rules, conventions, critical gotchas |
| `protocol_reference.json` | All protocol constants, bitfield maps, example frames — the "source of truth" |
| `DOC012721EN-E...pdf` | Original Mirion manual (132 pages) — only §10.1 is relevant for this API |

## Project Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                      USER APPLICATION                            │
│   device.get_device_info()  /  device.get_measurements()         │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    client.py (AccuRad)                            │
│   High-level facade. Orchestrates request → transport → parse.   │
│   Also: stream_measurements(), context manager, scan_devices()   │
└──────────────────────┬───────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
┌─────────────────────┐  ┌─────────────────────────┐
│  connection/         │  │  protocol/               │
│  serial.py (USB)     │  │  requests.py → fixed     │
│  bluetooth.py (BLE)  │  │    byte sequences        │
│                      │  │  frame.py → validate     │
│  Sends raw bytes,    │  │    marker/LEN/ID/CRC     │
│  receives raw bytes  │  │  crc.py → CRC16 check    │
│                      │  │  parsers.py → struct      │
│  BLE: 1s delay,      │  │    unpack → dataclasses  │
│  2s heartbeat        │  │                           │
└─────────────────────┘  └────────────┬──────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │  models/                 │
                         │  device_info.py          │
                         │  device_data.py          │
                         │  system_state.py         │
                         │  datetime.py (bitfields) │
                         │  enums.py                │
                         │                          │
                         │  Frozen dataclasses,     │
                         │  type-safe, immutable    │
                         └─────────────────────────┘
```

## Request/Response Cycle

```
1. User calls    →  device.get_measurements()
2. client.py     →  picks DEVICE_DATA_REQUEST bytes from requests.py
3. connection    →  sends b'\x7E\x04\x00\x11\xA7\x1E\x43\xE7' over USB/BLE
4. AccuRad PRD   →  responds with binary frame
5. connection    →  scans for "#!AccuRad!#" start marker, reads LEN bytes
6. frame.py      →  extracts LEN, ID, payload, CRC
                    validates: payload_size = LEN - 4 (NOT LEN - 2!)
                    validates: crc16(payload) == received_crc
7. parsers.py    →  struct.unpack_from("<...") on payload → dataclass fields
                    applies business rules (battery None if USB, etc.)
8. Returns       →  DeviceData frozen dataclass to user
```

## Key Gotchas (memorize these)

1. **LEN = N + 4** (includes ID + CRC), not N + 2
2. **Bitfields**: `struct` can't do C bitfields → unpack uint32 then bitmask
3. **Battery %**: force `None` when USB connected
4. **BLE 1s delay**: mandatory after connect, before first request
5. **BLE 2.5s timeout**: send heartbeat every 2s or device disconnects
6. **Request bytes are SACRED**: never reconstruct, always use the exact sequences

## Getting Started (Development)

```bash
# Clone and setup
git clone <repo-url>
cd accurad
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev,bluetooth]"

# Verify
pytest                    # All tests pass
mypy --strict accurad/    # No type errors
ruff check accurad/       # No lint issues
```

## Test Strategy

- **Unit tests**: Use hex dumps from `protocol_reference.json` example frames
- **No hardware needed**: Mock serial/BLE for CI
- **Integration tests**: Marked with `@pytest.mark.hardware`, skipped in CI
