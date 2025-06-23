# sensor.py (root)
from .ofen.sensor import async_setup_entry as setup_ofen_sensors

async def async_setup_entry(hass, entry, async_add_entities):
    await setup_ofen_sensors(hass, entry, async_add_entities)
