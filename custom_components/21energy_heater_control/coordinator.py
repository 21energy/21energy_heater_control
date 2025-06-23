"""DataUpdateCoordinator for 21energy_heater_control."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_HOST

from .api import (
    HeaterControlApiClientAuthenticationError,
    HeaterControlApiClientError,
)
from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data import HeaterControlConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class HeaterControlDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    entry: HeaterControlConfigEntry
    
    def __init__(self, hass: HomeAssistant, entry: HeaterControlConfigEntry, logger, name, update_interval):
        self.entry=entry
        self.device = entry.data["device"]
        super().__init__(hass, logger=logger, name=name, update_interval=update_interval)
    
    @property
    def device_is_running(self) -> bool:
        """Return the availability."""
        if "status_running" in self.data:
            if self.data.get("status_running"):
                return self.last_update_success
        return False

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.data["device"])},
            name=f"{MANUFACTURER} {self.entry.data["model"]}",
            manufacturer=MANUFACTURER,
            model=self.entry.data["model"],
            sw_version=self.entry.data["app_version"],
            serial_number=self.entry.data["device"],
        )

    async def async_set_device_enable(self, key: str, value: bool) -> Any:
        if key == "enable":
            await self.entry.runtime_data.client.async_set_enable(value)
            self.data[key] = value

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            return await self.entry.runtime_data.client.async_get_data()
        except HeaterControlApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except HeaterControlApiClientError as exception:
            raise UpdateFailed(exception) from exception
