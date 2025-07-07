"""Number platform for 21energy_heater_control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)

from ..const import DOMAIN, LOGGER
from ..entity import HeaterControlEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import HeaterControlDataUpdateCoordinator
    from ..data import HeaterControlConfigEntry

ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="powertarget",
        icon="mdi:lightning-bolt",
        entity_registry_enabled_default=True,
        device_class=None,
        native_min_value=1,
        native_max_value=5,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeaterControlConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    LOGGER.debug("NUMBER async_setup_entry")
    async_add_entities(
        HeaterControlNumber(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class HeaterControlNumber(HeaterControlEntity, NumberEntity):
    """HeaterControlNumber class."""

    def __init__(
        self,
        coordinator: HeaterControlDataUpdateCoordinator,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the number class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = (
            f"{self.coordinator.device}_{self.entity_description.key}"
        )
        self.entity_id = (
            f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"
        )

    async def async_added_to_hass(self) -> None:
        # Ensure we listen for coordinator updates
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self) -> float | None:
        """Return the native value of the number."""
        value = self.coordinator.data.get(self.entity_description.key)
        return float(value) + 1 if value is not None else None

    @property
    def available(self) -> bool:
        """Return the availability."""
        if self.coordinator.device_is_running:
            return self.coordinator.last_update_success
        return False

    async def async_set_native_value(self, value: float) -> None:
        try:
            LOGGER.debug(
                f"async_set_native_value => {self.entity_description.key}:{value}-1 = {value - 1}"
            )

            if self.entity_description.key == "powertarget":
                value = int(round(value - 1))
                await self.coordinator.entry.runtime_data.client.async_set_powerTarget(
                    value
                )

            await self.coordinator.async_refresh()
            return self.coordinator.data.get(self.entity_description.key)
        except ValueError:
            return "unavailable"
