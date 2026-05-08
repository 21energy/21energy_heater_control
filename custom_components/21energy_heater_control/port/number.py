"""Number platform for 21port devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode

from ..const import DOMAIN, LOGGER
from ..entity import HeaterControlEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import HeaterControlDataUpdateCoordinator
    from ..data import HeaterControlConfigEntry

ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="power_level",
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
        hass: HomeAssistant,  # noqa: ARG001
        entry: HeaterControlConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    async_add_entities(
        PortNumber(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

    from .device_entities import setup_dynamic_device_numbers
    setup_dynamic_device_numbers(entry.runtime_data.coordinator, async_add_entities, entry)


class PortNumber(HeaterControlEntity, NumberEntity):
    """Number entity for 21port."""

    def __init__(
            self,
            coordinator: HeaterControlDataUpdateCoordinator,
            entity_description: NumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = "global_power_level"
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self.entity_description.key)
        return float(value) + 1 if value is not None else None

    @property
    def available(self) -> bool:
        if self.coordinator.device_is_running:
            return self.coordinator.last_update_success
        return False

    async def async_set_native_value(self, value: float) -> None:
        LOGGER.debug("async_set_native_value => power_level:%s-1=%s", value, value - 1)
        api_value = int(round(value - 1))
        from ..api import PortControlApiClient
        client = self.coordinator.entry.runtime_data.client
        assert isinstance(client, PortControlApiClient)
        await client.async_set_powerLevel(api_value)
        await self.coordinator.async_refresh()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
