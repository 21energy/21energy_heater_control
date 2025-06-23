"""The 12engergy Heater Control integration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import HeaterControlApiClient
from .const import DOMAIN, CONF_POLLING_INTERVAL, LOGGER
from .coordinator import HeaterControlDataUpdateCoordinator
from .data import HeaterControlData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import HeaterControlConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeaterControlConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = HeaterControlDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=entry.data[CONF_POLLING_INTERVAL]),
    )
    entry.runtime_data = HeaterControlData(
        client=HeaterControlApiClient(
            host=entry.data[CONF_HOST],
            session=async_get_clientsession(hass),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: HeaterControlConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: HeaterControlConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)