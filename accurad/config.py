"""Centralized configuration for the AccuRad PRD API.

Provides :class:`AccuRadConfig` to group all tunable parameters
in a single place instead of scattering them across factory methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from accurad._constants import (
    BLE_KEEPALIVE_INTERVAL_S,
    DEFAULT_BLE_CONNECT_TIMEOUT_S,
    DEFAULT_READ_TIMEOUT_S,
    DEFAULT_WRITE_TIMEOUT_S,
)


@dataclass
class AccuRadConfig:
    """Configuration bundle for an AccuRad client.

    All values have sensible defaults matching the protocol
    requirements. Override only what you need.

    Example:
        >>> cfg = AccuRadConfig(retries=3, retry_delay=1.0)
        >>> device = AccuRad.connect_usb("COM3", config=cfg)

    """

    # Timeouts
    read_timeout: float = DEFAULT_READ_TIMEOUT_S
    write_timeout: float = DEFAULT_WRITE_TIMEOUT_S
    connect_timeout: float = DEFAULT_BLE_CONNECT_TIMEOUT_S

    # Retry
    retries: int = 0
    retry_delay: float = 0.5

    # BLE-specific
    keepalive: bool = True
    keepalive_interval: float = field(
        default=BLE_KEEPALIVE_INTERVAL_S,
    )

    # Diagnostics
    log_frames: bool = False
    """When True, log raw frame hex at DEBUG level."""
