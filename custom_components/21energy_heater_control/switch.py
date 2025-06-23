# switch.py (root)
from .ofen.switch import async_setup_entry as setup_ofen_switch

async def async_setup_entry(hass, entry, async_add_entities):
    await setup_ofen_switch(hass, entry, async_add_entities)
