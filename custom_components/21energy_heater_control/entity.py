"""Entity class for 21energy_heater_control."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .coordinator import HeaterControlDataUpdateCoordinator


# Must match entity_ids already stored in users' entity registries.
def build_entity_id(platform: Platform, *parts: str) -> str:
    return f"{platform}.{slugify('_'.join(parts))}"


class HeaterControlEntity(CoordinatorEntity[HeaterControlDataUpdateCoordinator]):
    """HeaterControlEntity class."""

    # _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: HeaterControlDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.entry.entry_id
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict:
        return self.coordinator.device_info
