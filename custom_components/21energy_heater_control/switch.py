"""Swtich platform for 21energy_heater_control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import (
    REVOLUTIONS_PER_MINUTE
)
from .entity import HeaterControlEntity
from .const import DOMAIN, STATE_ON, STATE_OFF
import asyncio

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import HeaterControlDataUpdateCoordinator
    from .data import HeaterControlConfigEntry

@dataclass
class ExtSwitchEntityDescription(SwitchEntityDescription):
    icon_off: str | None = None

ENTITY_DESCRIPTIONS = (
    ExtSwitchEntityDescription(
        key="enable",
        icon="mdi:radiator",
        icon_off="mdi:radiator-off",
        entity_registry_enabled_default=True,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HeaterControlConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        HeaterControlSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class HeaterControlSwitch(HeaterControlEntity, SwitchEntity):
    """HeaterControlSwitch class."""

    def __init__(
        self,
        coordinator: HeaterControlDataUpdateCoordinator,
        entity_description: ExtSwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"
        self._attr_icon_off = self.entity_description.icon_off

    async def async_turn_on(self, **kwargs):
        """Turn on the switch."""
        try:
            await self.coordinator.async_set_device_enable(self.entity_description.key, True)
            self.async_write_ha_state()
        except ValueError:
            return "unavailable"

    async def async_turn_off(self, **kwargs):
        """Turn off the switch."""
        try:
            await self.coordinator.async_set_device_enable(self.entity_description.key, False)
            self.async_write_ha_state()
        except ValueError:
            return "unavailable"

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.data.get(self.entity_description.key)
            if value is None or value == "":
                value = None
        except KeyError:
            _LOGGER.warning(f"is_on caused KeyError for: {self.entity_description.key}")
            value = None
        except TypeError:
            return None
        return value

    @property
    def state(self) -> Literal["on", "off"] | None:
        """Return the state."""
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF

    @property
    def icon(self):
        """Return the icon of the switch."""
        if self._attr_icon_off is not None and self.state == STATE_OFF:
            return self._attr_icon_off
        else:
            return super().icon

    @property
    def available(self) -> bool:
        """Return the availability."""
        return self.coordinator.last_update_success