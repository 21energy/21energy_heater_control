"""BinarySensor platform for 21energy_heater_control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.const import (
    REVOLUTIONS_PER_MINUTE
)
from .entity import HeaterControlEntity
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import HeaterControlDataUpdateCoordinator
    from .data import HeaterControlConfigEntry

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="status_running",
        icon="mdi:electric-switch",
        entity_registry_enabled_default=True,
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BinarySensorEntityDescription(
        key="connected",
        icon="mdi:electric-switch",
        entity_registry_enabled_default=True,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HeaterControlConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary binarysensor platform."""
    async_add_entities(
        HeaterControlBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class HeaterControlBinarySensor(HeaterControlEntity, BinarySensorEntity):
    """HeaterControlBinarySensor class."""

    def __init__(
        self,
        coordinator: HeaterControlDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binarysensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the native value of the binarysensor."""
        if self.entity_description.key == "connected":
            return self.coordinator.data.get("status")
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return the availability."""
        return self.coordinator.last_update_success
