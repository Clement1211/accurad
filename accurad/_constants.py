"""Protocol constants for the AccuRad PRD communication protocol.

All values extracted from DOC012721EN-E, Section 10.1.
These are immutable protocol-level constants — never modify them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Frame format
# ---------------------------------------------------------------------------

START_MARKER: bytes = b"#!AccuRad!#"
"""11-byte ASCII marker that begins every response frame."""

START_MARKER_LENGTH: int = 11
LEN_FIELD_SIZE: int = 2
ID_FIELD_SIZE: int = 2
CRC_FIELD_SIZE: int = 2

# LEN = ID(2) + Payload(N) + CRC(2) = N + 4
# Therefore: payload_size = LEN - 4
LEN_OVERHEAD: int = 4
"""Bytes included in LEN besides payload: ID(2) + CRC(2)."""

# ---------------------------------------------------------------------------
# CRC16
# ---------------------------------------------------------------------------

POLYNOM16: int = 0xAC5E
"""CRC16 polynomial. CRC computed on payload bytes only."""

CRC_INITIAL: int = 0xFFFF
"""Initial CRC accumulator value."""

# ---------------------------------------------------------------------------
# Request sequences (send as-is, DO NOT reconstruct)
# ---------------------------------------------------------------------------

DEVICE_INFO_REQUEST: bytes = bytes([0x7E, 0x04, 0x00, 0x10, 0xA7, 0x07, 0x46, 0xE7])
"""Fixed 8-byte request for device information (frame ID=0)."""

DEVICE_DATA_REQUEST: bytes = bytes([0x7E, 0x04, 0x00, 0x11, 0xA7, 0x1E, 0x43, 0xE7])
"""Fixed 8-byte request for device measurements (frame ID=1)."""

# ---------------------------------------------------------------------------
# Frame IDs
# ---------------------------------------------------------------------------

FRAME_ID_DEVICE_INFO: int = 0
FRAME_ID_DEVICE_DATA: int = 1

# ---------------------------------------------------------------------------
# Expected payload sizes (for validation)
# ---------------------------------------------------------------------------

DEVICE_INFO_PAYLOAD_SIZE: int = 65
"""Expected payload size for ID=0 response."""

DEVICE_DATA_PAYLOAD_SIZE: int = 47
"""Expected payload size for ID=1 response."""

# ---------------------------------------------------------------------------
# Bluetooth BLE
# ---------------------------------------------------------------------------

BLE_UART_SERVICE_UUID: str = "49535343-FE7D-4AE5-8FA9-9FAFD205E455"
"""Nordic UART Service UUID used by the AccuRad PRD."""

BLE_UART_TX_UUID: str = "49535343-1E4D-4BD9-BA61-23C647249616"
"""TX characteristic UUID (Notify + Write)."""

BLE_POST_CONNECT_DELAY_S: float = 1.0
"""Mandatory delay after BLE connect before first request (seconds)."""

BLE_KEEPALIVE_INTERVAL_S: float = 2.0
"""Heartbeat interval to prevent BLE disconnect (device timeout = 2.5s)."""

BLE_DEVICE_TIMEOUT_S: float = 2.5
"""Device disconnects if no valid message received within this window."""

BLE_DISCOVERABLE_DURATION_S: float = 60.0
"""Duration the device stays discoverable after NFC scan or disconnect."""

# ---------------------------------------------------------------------------
# Timeouts (defaults, user-configurable)
# ---------------------------------------------------------------------------

DEFAULT_READ_TIMEOUT_S: float = 3.0
DEFAULT_WRITE_TIMEOUT_S: float = 1.0
DEFAULT_USB_CONNECT_TIMEOUT_S: float = 2.0
DEFAULT_BLE_CONNECT_TIMEOUT_S: float = 15.0

# ---------------------------------------------------------------------------
# Timezone lookup table (index -> label)
# ---------------------------------------------------------------------------

TIMEZONE_TABLE: dict[int, str] = {
    0: "UTC-12:00",
    1: "UTC-11:00",
    2: "UTC-10:00 (Honolulu)",
    3: "UTC-09:30 (Marquesas)",
    4: "UTC-09:00 (Anchorage)",
    5: "UTC-08:00 (Los Angeles)",
    6: "UTC-07:00 (Phoenix)",
    7: "UTC-06:00 (Chicago)",
    8: "UTC-05:00 (New York)",
    9: "UTC-04:00 (Caracas)",
    10: "UTC-03:30 (St. John's)",
    11: "UTC-03:00 (Buenos Aires)",
    12: "UTC-02:00 (Fernando de Noronha)",
    13: "UTC-01:00 (Cape Verde)",
    14: "UTC+00:00 (London)",
    15: "UTC+01:00 (Paris)",
    16: "UTC+02:00 (Athens)",
    17: "UTC+03:00 (Moscow)",
    18: "UTC+03:30 (Tehran)",
    19: "UTC+04:00 (Dubai)",
    20: "UTC+04:30 (Kabul)",
    21: "UTC+05:00 (Karachi)",
    22: "UTC+05:30 (Delhi)",
    23: "UTC+05:45 (Kathmandu)",
    24: "UTC+06:00 (Dhaka)",
    25: "UTC+06:30 (Yangon)",
    26: "UTC+07:00 (Bangkok)",
    27: "UTC+08:00 (Beijing)",
    28: "UTC+08:45 (Eucla)",
    29: "UTC+09:00 (Tokyo)",
    30: "UTC+09:30 (Adelaide)",
    31: "UTC+10:00 (Sydney)",
    32: "UTC+10:30 (NSW)",
    33: "UTC+11:00 (Noumea)",
    34: "UTC+12:00 (Auckland)",
    35: "UTC+12:45 (Chatham)",
    36: "UTC+13:00 (Apia)",
    37: "UTC+14:00 (Kiribati)",
}
