# binary_sensor.py (root)
from .ofen.binary_sensor import async_setup_entry as setup_ofen_binary_sensor

async def async_setup_entry(hass, entry, async_add_entities):
    await setup_ofen_binary_sensor(hass, entry, async_add_entities)
