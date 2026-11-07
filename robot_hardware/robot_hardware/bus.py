from .odrive_can import CanBus


def open_bus(channel: str = "can0", interface: str = "socketcan",
             bitrate: int = 500000) -> CanBus:
    """Open the ODrive bus wrapper used by ``ODriveAxis``.

    ``ODriveAxis`` relies on ``register()`` for its receive callbacks, so callers
    must not pass a raw ``python-can`` bus here.
    """
    return CanBus(interface=interface, channel=channel, bitrate=bitrate)
