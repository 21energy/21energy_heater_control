"""Switch platform for 21port devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from homeassistant.components.switch import SwitchEntity

from ..const import DOMAIN, STATE_OFF, STATE_ON
from ..entity import HeaterControlEntity
from ..ofen.switch import ExtSwitchEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import HeaterControlDataUpdateCoordinator
    from ..data import HeaterControlConfigEntry

ENTITY_DESCRIPTIONS = (
    ExtSwitchEntityDescription(
        key="enable",
        icon="mdi:pickaxe",
        icon_off=None,
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,  # noqa: ARG001
        entry: HeaterControlConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        PortSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

    from .device_entities import setup_dynamic_device_switches
    setup_dynamic_device_switches(entry.runtime_data.coordinator, async_add_entities, entry)


class PortSwitch(HeaterControlEntity, SwitchEntity):
    """Switch entity for 21port."""

    def __init__(
            self,
            coordinator: HeaterControlDataUpdateCoordinator,
            entity_description: ExtSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = "global_enable"
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_device_enable(self.entity_description.key, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_device_enable(self.entity_description.key, False)
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.data.get(self.entity_description.key)
            if value is None or value == "":
                return None
        except (KeyError, TypeError):
            return None
        return value

    @property
    def state(self) -> Literal["on", "off"] | None:
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
