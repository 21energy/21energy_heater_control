"""Entity class for 21energy_heater_control."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import HeaterControlDataUpdateCoordinator


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
