"""Binary sensor platform for 21energy_heater_control."""

from .device_registry import get_platform_setup


async def async_setup_entry(hass, entry, async_add_entities):
    await get_platform_setup(entry.data, "binary_sensor")(hass, entry, async_add_entities)
