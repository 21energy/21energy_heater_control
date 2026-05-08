"""Central registry mapping device types to their implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Type

from .api import DeviceApiClientBase, HeaterControlApiClient, PortControlApiClient
from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_OFEN, DEVICE_TYPE_PORT
# Sub-package platform modules — imported here at load time (synchronously)
# so get_platform_setup never calls importlib inside the async event loop.
from .ofen import binary_sensor as _ofen_binary_sensor
from .ofen import number as _ofen_number
from .ofen import sensor as _ofen_sensor
from .ofen import switch as _ofen_switch
from .port import binary_sensor as _port_binary_sensor
from .port import number as _port_number
from .port import sensor as _port_sensor
from .port import switch as _port_switch

if TYPE_CHECKING:
    import aiohttp


@dataclass(frozen=True)
class DeviceTypeRegistration:
    client_class: Type[DeviceApiClientBase]
    platforms: dict[str, Callable] = field(default_factory=dict)


DEVICE_REGISTRY: dict[str, DeviceTypeRegistration] = {
    DEVICE_TYPE_OFEN: DeviceTypeRegistration(
        client_class=HeaterControlApiClient,
        platforms={
            "sensor": _ofen_sensor.async_setup_entry,
            "switch": _ofen_switch.async_setup_entry,
            "binary_sensor": _ofen_binary_sensor.async_setup_entry,
            "number": _ofen_number.async_setup_entry,
        },
    ),
    DEVICE_TYPE_PORT: DeviceTypeRegistration(
        client_class=PortControlApiClient,
        platforms={
            "sensor": _port_sensor.async_setup_entry,
            "switch": _port_switch.async_setup_entry,
            "binary_sensor": _port_binary_sensor.async_setup_entry,
            "number": _port_number.async_setup_entry,
        },
    ),
}


def create_client(entry_data: dict, session: aiohttp.ClientSession) -> DeviceApiClientBase:
    """Instantiate the right API client for the device type in entry_data."""
    from homeassistant.const import CONF_HOST

    device_type = entry_data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_OFEN)
    reg = DEVICE_REGISTRY[device_type]
    if device_type == DEVICE_TYPE_PORT:
        return reg.client_class(
            host=entry_data[CONF_HOST],
            session=session,
        )
    return reg.client_class(host=entry_data[CONF_HOST], session=session)


def get_platform_setup(entry_data: dict, platform: str) -> Callable:
    """Return the async_setup_entry function for the device type + platform."""
    device_type = entry_data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_OFEN)
    return DEVICE_REGISTRY[device_type].platforms[platform]
