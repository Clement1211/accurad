"""AccuRad — high-level client for the AccuRad PRD radiation detector.

This is the main entry point for users of the library. It provides a
clean, transport-agnostic interface for reading device information
and measurement data.

Example:
    >>> from accurad import AccuRad
    >>> with AccuRad.connect_usb("COM3") as device:
    ...     info = device.get_device_info()
    ...     data = device.get_measurements()
    ...     print(f"Dose rate: {data.merged.dose_rate_usv_h:.4f} uSv/h")

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from accurad._constants import DEVICE_DATA_REQUEST, DEVICE_INFO_REQUEST
from accurad.connection.serial import SerialConnection
from accurad.exceptions import UnexpectedFrameIDError
from accurad.protocol.frame import parse_frame
from accurad.protocol.parsers import parse_device_data, parse_device_info

if TYPE_CHECKING:
    from accurad.connection.base import AccuRadConnection
    from accurad.models.device_data import DeviceData
    from accurad.models.device_info import DeviceInfo
    pass


class AccuRad:
    """High-level client for communicating with an AccuRad PRD.

    Use the factory classmethods :meth:`connect_usb` or :meth:`connect_bluetooth`
    to create an instance. Supports the context manager protocol (``with`` statement).

    Args:
        connection: An established :class:`AccuRadConnection` transport.

    """

    def __init__(self, connection: AccuRadConnection) -> None:
        """Initialize with an established connection."""
        self._connection = connection

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def connect_usb(
        cls,
        port: str,
        read_timeout: float = 3.0,
        write_timeout: float = 1.0,
    ) -> AccuRad:
        """Connect to an AccuRad PRD via USB COM port.

        Args:
            port: Serial port identifier (e.g. "COM3", "/dev/ttyUSB0").
            read_timeout: Read timeout in seconds.
            write_timeout: Write timeout in seconds.

        Returns:
            Connected AccuRad client instance.

        """
        conn = SerialConnection(
            port=port,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        )
        conn.connect()
        return cls(conn)

    @classmethod
    def connect_bluetooth(
        cls,
        address: str,
        connect_timeout: float = 5.0,
        read_timeout: float = 3.0,
    ) -> AccuRad:
        """Connect to an AccuRad PRD via Bluetooth Low Energy.

        Includes the mandatory 1-second post-connect delay.

        Args:
            address: BLE MAC address or device name.
            connect_timeout: Connection timeout in seconds.
            read_timeout: Read timeout in seconds.

        Returns:
            Connected AccuRad client instance.

        """
        from accurad.connection.bluetooth import BluetoothConnection

        conn = BluetoothConnection(
            address=address,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )
        conn.connect()
        return cls(conn)

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    def get_device_info(self) -> DeviceInfo:
        """Request and return device information (frame ID=0).

        Sends the fixed device info request sequence and parses the response
        into a :class:`~accurad.models.device_info.DeviceInfo` dataclass.

        Returns:
            Device information including manufacturer, serial number,
            firmware version, and device clock.

        Raises:
            ProtocolError: If the response frame is invalid.
            CRCMismatchError: If the CRC check fails.
            ReadTimeoutError: If the device doesn't respond.

        """
        self._connection.send(DEVICE_INFO_REQUEST)
        raw = self._connection.receive()
        frame = parse_frame(raw)

        if frame.frame_id != 0:
            raise UnexpectedFrameIDError(expected=0, received=frame.frame_id)

        return parse_device_info(frame.payload)

    def get_measurements(self) -> DeviceData:
        """Request and return current measurements (frame ID=1).

        Sends the fixed measurement request sequence and parses the response
        into a :class:`~accurad.models.device_data.DeviceData` dataclass.

        Returns:
            Current measurements including dose rate, count rate,
            accumulated dose, battery status, and system state.

        Raises:
            ProtocolError: If the response frame is invalid.
            CRCMismatchError: If the CRC check fails.
            ReadTimeoutError: If the device doesn't respond.

        """
        self._connection.send(DEVICE_DATA_REQUEST)
        raw = self._connection.receive()
        frame = parse_frame(raw)

        if frame.frame_id != 1:
            raise UnexpectedFrameIDError(expected=1, received=frame.frame_id)

        return parse_device_data(frame.payload)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        """Close the connection to the device."""
        self._connection.disconnect()

    @property
    def is_connected(self) -> bool:
        """Return True if the connection to the device is active."""
        return self._connection.is_connected

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> AccuRad:
        """Enter context — connection is already established."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context — disconnect from the device."""
        self.disconnect()

    def __repr__(self) -> str:
        """Return a string representation of the client."""
        status = "connected" if self.is_connected else "disconnected"
        return f"AccuRad({status})"
