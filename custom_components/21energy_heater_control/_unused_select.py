# """Select platform for 21energy_heater_control."""
#
# from __future__ import annotations
#
# from typing import TYPE_CHECKING
#
# from homeassistant.components.select import SelectEntity, SelectEntityDescription
# from homeassistant.const import (
#     REVOLUTIONS_PER_MINUTE
# )
# from .entity import HeaterControlEntity
# from .const import DOMAIN, DEVICE_CLASS_ENUM, ENUM_AUTOMANUAL
#
# if TYPE_CHECKING:
#     from homeassistant.core import HomeAssistant
#     from homeassistant.helpers.entity_platform import AddEntitiesCallback
#
#     from .coordinator import HeaterControlDataUpdateCoordinator
#     from .data import HeaterControlConfigEntry
#
# ENTITY_DESCRIPTIONS = (
#     SelectEntityDescription(
#         key="fan_mode",
#         icon="mdi:fan",
#         entity_registry_enabled_default=True,
#         device_class=DEVICE_CLASS_ENUM,
#         options=ENUM_AUTOMANUAL,
#     ),
# )
#
#
# async def async_setup_entry(
#     hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
#     entry: HeaterControlConfigEntry,
#     async_add_entities: AddEntitiesCallback,
# ) -> None:
#     """Set up the select platform."""
#     async_add_entities(
#         HeaterControlSelect(
#             coordinator=entry.runtime_data.coordinator,
#             entity_description=entity_description,
#         )
#         for entity_description in ENTITY_DESCRIPTIONS
#     )
#
#
# class HeaterControlSelect(HeaterControlEntity, SelectEntity):
#     """HeaterControlSelect Select class."""
#
#     def __init__(
#         self,
#         coordinator: HeaterControlDataUpdateCoordinator,
#         entity_description: SelectEntityDescription,
#     ) -> None:
#         """Initialize the select class."""
#         super().__init__(coordinator)
#         self.entity_description = entity_description
#         self._attr_translation_key = self.entity_description.key
#         self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
#         self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"
#
#     @property
#     def current_option(self) -> str | None:
#         try:
#             value = self.coordinator.data.get(self.entity_description.key)
#             if value is None or value == "":
#                 value = 'unknown'
#             elif isinstance(value, bool):
#                 # for "switches" that we want to show as selects, we need to convert
#                 # the bool True/False to 1 and 0
#                 if value:
#                     value = "1"
#                 else:
#                     value = "0"
#         except KeyError:
#             value = "unknown"
#         except TypeError:
#             return None
#         return str(value)
#
#     async def async_select_option(self, option: str) -> None:
#         try:
#             if self.entity_description.key == "fan_mode":
#                 await self.coordinator.entry.runtime_data.client.async_set_fanMode(option)
#             await self.coordinator.async_refresh()
#             return self.coordinator.data.get(self.entity_description.key)
#         except ValueError:
#             return "unavailable"
#
#     @property
#     def available(self) -> bool:
#         """Return the availability."""
#         if self.coordinator.device_is_running:
#             return self.coordinator.last_update_success
#         return False