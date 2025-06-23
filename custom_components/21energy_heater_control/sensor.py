"""Sensor platform for 21energy_heater_control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
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
    SensorEntityDescription(
        key="status_temperature",
        icon="mdi:thermometer",
        entity_registry_enabled_default=True,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="powertarget_watt",
        icon="mdi:lightning-bolt-outline",
        entity_registry_enabled_default=True,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="power_limit",
        icon="mdi:lightning-bolt-outline",
        entity_registry_enabled_default=True,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
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
        key="hashrate_5s",
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="hashrate_1m",
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="hashrate_5m",
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="hashrate_15m",
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="hashrate_24h",
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="hashrate_av",
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="poolstatus",
        icon="mdi:connection",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="foundblocks",
        icon="mdi:numeric",
        entity_registry_enabled_default=True,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HeaterControlConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        HeaterControlSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class HeaterControlSensor(HeaterControlEntity, SensorEntity):
    """HeaterControlSensor class."""

    def __init__(
        self,
        coordinator: HeaterControlDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = f"{self.coordinator.device}_{self.entity_description.key}"
        self.entity_id = f"{DOMAIN}.{self.coordinator.device}.{self.entity_description.key}"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return the availability."""
        if self.coordinator.device_is_running:
            return self.coordinator.last_update_success
        return False