# AccuRad PRD API — Developer Guide

## Reference Documents

| Document | Purpose |
|---|---|
| `PRD.md` | Requirements, architecture, milestones — the "what" and "why" |
| `CLAUDE.md` | AI assistant rules, conventions, critical implementation gotchas |
| `protocol_reference.json` | All protocol constants, bitfield maps, example frames |
| `DOC012721EN-E...pdf` | Original Mirion manual (132 pages) — only §10.1 is relevant |

## Architecture & Data Flow

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
│   Retry logic, thread lock, auto-reconnect, discovery, ping.     │
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
│  2s heartbeat,       │  │                           │
│  auto keep-alive     │  │                           │
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
                         │  type-safe, immutable,   │
                         │  to_dict() for JSON      │
                         └─────────────────────────┘
```

## Request/Response Cycle

```
1. User calls    →  device.get_measurements()
2. client.py     →  acquires thread lock
                    picks DEVICE_DATA_REQUEST bytes from _constants.py
3. _request()    →  sends request, receives response (with retry logic)
4. connection    →  sends b'\x7E\x04\x00\x11\xA7\x1E\x43\xE7' over USB/BLE
5. AccuRad PRD   →  responds with binary frame
6. connection    →  scans for "#!AccuRad!#" start marker, reads LEN bytes
7. frame.py      →  extracts LEN, ID, payload, CRC
                    validates: payload_size = LEN - 4 (NOT LEN - 2!)
                    validates: crc16(ID + payload) == received_crc
                    validates: payload_size matches expected for frame ID
8. parsers.py    →  struct.unpack_from("<...") on payload → dataclass fields
                    applies business rules (battery None if USB, etc.)
9. Returns       →  DeviceData frozen dataclass to user
```

## Critical Implementation Rules

1. **LEN = N + 4** (includes ID + CRC), not N + 2
2. **CRC on ID + Payload** — "XXXXX" in the manual = everything between LEN and CRC
3. **Bitfields**: `struct` can't decode C bitfields → unpack uint32 then bitmask
4. **Battery %**: force `None` when USB connected (hardware reports garbage)
5. **BLE 1s delay**: mandatory after connect, before first request
6. **BLE 2.5s timeout**: device disconnects if no valid message — keep-alive sends heartbeat every 2s
7. **Request bytes are SACRED**: never reconstruct them, always use the exact fixed sequences

## Error Handling Architecture

```
AccuRadError (base)
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

Each exception has:
- `recoverable: bool` — whether retrying might succeed
- `suggestion: str | None` — human-readable hint

## Thread Safety

The `AccuRad` client uses a `threading.Lock` on all request/response cycles. This means:
- `stream_measurements()` + `start_logging()` can run concurrently
- Multiple threads can call `get_measurements()` safely (serialized)
- BLE keep-alive runs on a separate timer thread — does not conflict

## Logging

All modules use `logging.getLogger("accurad.<module>")`. No `print()` calls anywhere.

| Logger | Level | What it logs |
|---|---|---|
| `accurad.client` | INFO | Connect/disconnect events |
| `accurad.client` | DEBUG | Request type, parsed results summary |
| `accurad.connection.serial` | INFO | Port open/close |
| `accurad.connection.serial` | DEBUG | TX/RX hex dumps |
| `accurad.connection.bluetooth` | INFO | Scan, connect, disconnect |
| `accurad.connection.bluetooth` | DEBUG | TX/RX hex, keep-alive |
| `accurad.protocol.frame` | DEBUG | Frame parsing, CRC values |
| `accurad.protocol.frame` | WARNING | CRC mismatch, malformed frames |
| `accurad.streaming` | INFO | Stream start, logging start/stop |
| `accurad.streaming` | WARNING | Poll failures in logger |

## Development Setup

```bash
git clone https://github.com/clementMusic/accurad.git
cd accurad
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev,bluetooth]"
```

## Running Checks

```bash
# All three must pass before committing
pytest                     # 33 unit tests
mypy --strict accurad/     # 0 errors on 21 source files
ruff check accurad/        # 0 lint errors
```

## Test Strategy

- **Unit tests**: Use hex dumps from `protocol_reference.json` example frames
- **No hardware needed**: All unit tests work without a device
- **Integration tests**: Marked with `@pytest.mark.hardware`, skipped in CI
- **Hardware test**: `python -c "from accurad import AccuRad; d = AccuRad.connect_usb('COM3'); print(d.get_measurements()); d.disconnect()"`
