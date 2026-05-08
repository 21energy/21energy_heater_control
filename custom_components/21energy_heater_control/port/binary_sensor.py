"""Binary sensor platform for 21port devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from ..const import DOMAIN
from ..entity import HeaterControlEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import HeaterControlDataUpdateCoordinator
    from ..data import HeaterControlConfigEntry

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="pool_alive",
        icon="mdi:pool",
        entity_registry_enabled_default=True,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,  # noqa: ARG001
        entry: HeaterControlConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_add_entities(
        PortBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class PortBinarySensor(HeaterControlEntity, BinarySensorEntity):
    """Binary sensor entity for 21port."""

    def __init__(
            self,
            coordinator: HeaterControlDataUpdateCoordinator,
            entity_description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
