# number.py (root)
from .ofen.number import async_setup_entry as setup_ofen_numbers


async def async_setup_entry(hass, entry, async_add_entities):
    await setup_ofen_numbers(hass, entry, async_add_entities)
