"""Sensor platform for 21port devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower

from ..const import DOMAIN
from ..entity import HeaterControlEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import HeaterControlDataUpdateCoordinator
    from ..data import HeaterControlConfigEntry

ALWAYS_AVAILABLE_SENSORS = {"device_count", "version", "pool_1", "pool_2"}

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="device_count",
        icon="mdi:devices",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="pool_status",
        icon="mdi:connection",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="power_consumption",
        icon="mdi:flash",
        entity_registry_enabled_default=True,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="total_hashrate",
        icon="mdi:numeric",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="TH/s",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="pool_1",
        icon="mdi:pool",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="pool_2",
        icon="mdi:pool",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="version",
        icon="mdi:tag",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,  # noqa: ARG001
        entry: HeaterControlConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        PortSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

    from .device_entities import setup_dynamic_device_sensors, setup_device_cleanup
    setup_dynamic_device_sensors(entry.runtime_data.coordinator, async_add_entities, entry)
    setup_device_cleanup(entry.runtime_data.coordinator, entry)


class PortSensor(HeaterControlEntity, SensorEntity):
    """Sensor entity for 21port."""

    def __init__(
            self,
            coordinator: HeaterControlDataUpdateCoordinator,
            entity_description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"

    @property
    def native_value(self):
        key = self.entity_description.key
        if key == "pool_1":
            pool_config = self.coordinator.data.get("pool_config") or []
            p = pool_config[0] if len(pool_config) > 0 else {}
            return f"{p.get('user')}\n{p.get('url')}" if p else None
        if key == "pool_2":
            pool_config = self.coordinator.data.get("pool_config") or []
            p = pool_config[1] if len(pool_config) > 1 else {}
            return f"{p.get('user')}\n{p.get('url')}" if p else None
        return self.coordinator.data.get(key)

    @property
    def available(self) -> bool:
        if self.entity_description.key in ALWAYS_AVAILABLE_SENSORS or self.coordinator.device_is_running:
            return self.coordinator.last_update_success
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
