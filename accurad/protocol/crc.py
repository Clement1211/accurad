"""CRC16 implementation for the AccuRad PRD protocol.

Polynomial: 0xAC5E with zero-avoidance.
Faithfully translated from the C source in DOC012721EN-E, Section 10.1.

The CRC is computed on **ID + payload** (referred to as "XXXXX" in the
manual's frame format). It does NOT include the start marker or LEN field.
"""

from __future__ import annotations

from accurad._constants import CRC_INITIAL, POLYNOM16


def crc16(data: bytes | bytearray) -> int:
    """Compute the AccuRad CRC16 checksum over *data*.

    Algorithm (from manual):
        1. Initialize CRC = 0xFFFF
        2. For each byte: CRC ^= byte
        3. If CRC == 0: CRC = 1 (zero avoidance)
        4. For 8 bits: parity = CRC & 1; CRC >>= 1; if parity: CRC ^= 0xAC5E
        5. Return CRC

    Args:
        data: ID + payload bytes to checksum.

    Returns:
        16-bit CRC value.

    """
    crc: int = CRC_INITIAL

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
