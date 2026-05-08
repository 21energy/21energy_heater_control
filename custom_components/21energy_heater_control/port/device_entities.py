"""Dynamic per-device entities for 21PORT mining devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import UnitOfPower, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from ..const import DOMAIN, LOGGER, STATE_OFF, STATE_ON
from ..entity import HeaterControlEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import HeaterControlDataUpdateCoordinator
    from ..data import HeaterControlConfigEntry

DEVICE_REMOVAL_DELAY = 60  # seconds


def _get_device(coordinator: HeaterControlDataUpdateCoordinator, device_id: str) -> dict | None:
    devices = (coordinator.data or {}).get("devices") or []
    return next((d for d in devices if d["id"] == device_id), None)


def _safe_entity_id(device_id: str) -> str:
    """Sanitize device_id for use in entity_id (replace dots with underscores)."""
    return device_id.replace(".", "_")


class PortDeviceSensor(HeaterControlEntity, SensorEntity):
    """Sensor for a per-device field on a 21PORT mining device."""

    def __init__(
            self,
            coordinator: HeaterControlDataUpdateCoordinator,
            device: dict,
            key: str,
            label: str,
            unit: str | None = None,
            device_class: str | None = None,
            state_class: str | None = None,
            icon: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._key = key
        self._attr_name = f"{device['model']} {label}"
        self._attr_unique_id = f"{coordinator.device}_{device['id']}_{key}"
        self.entity_id = f"{DOMAIN}.{coordinator.device}_{_safe_entity_id(device['id'])}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon

    @property
    def native_value(self):
        device = _get_device(self.coordinator, self._device_id)
        if device is None:
            return None
        return device.get(self._key)

    @property
    def available(self) -> bool:
        return (
                self.coordinator.last_update_success
                and _get_device(self.coordinator, self._device_id) is not None
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class PortDeviceSwitch(HeaterControlEntity, SwitchEntity):
    """Switch to enable/disable an individual 21PORT mining device."""

    def __init__(self, coordinator: HeaterControlDataUpdateCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._attr_name = f"{device['model']} Enabled"
        self._attr_unique_id = f"{coordinator.device}_{device['id']}_enabled"
        self.entity_id = f"{DOMAIN}.{coordinator.device}_{_safe_entity_id(device['id'])}_enabled"
        self._attr_icon = "mdi:pickaxe"

    @property
    def is_on(self) -> bool | None:
        device = _get_device(self.coordinator, self._device_id)
        if device is None:
            return None
        return device.get("enabled")

    @property
    def state(self) -> Literal["on", "off"] | None:
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF

    @property
    def available(self) -> bool:
        return (
                self.coordinator.last_update_success
                and _get_device(self.coordinator, self._device_id) is not None
        )

    async def async_turn_on(self, **kwargs) -> None:
        from ..api import PortControlApiClient
        client = self.coordinator.entry.runtime_data.client
        assert isinstance(client, PortControlApiClient)
        await client.async_set_device_enable(self._device_id, True)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        from ..api import PortControlApiClient
        client = self.coordinator.entry.runtime_data.client
        assert isinstance(client, PortControlApiClient)
        await client.async_set_device_enable(self._device_id, False)
        await self.coordinator.async_refresh()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class PortDeviceNumber(HeaterControlEntity, NumberEntity):
    """Power level slider for an individual 21PORT mining device."""

    def __init__(self, coordinator: HeaterControlDataUpdateCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._attr_name = f"{device['model']} Power Level"
        self._attr_unique_id = f"{coordinator.device}_{device['id']}_power_level"
        self.entity_id = f"{DOMAIN}.{coordinator.device}_{_safe_entity_id(device['id'])}_power_level"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 5
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float | None:
        device = _get_device(self.coordinator, self._device_id)
        if device is None:
            return None
        value = device.get("powerLevel")
        return float(value) + 1 if value is not None else None

    @property
    def available(self) -> bool:
        return (
                self.coordinator.last_update_success
                and _get_device(self.coordinator, self._device_id) is not None
        )

    async def async_set_native_value(self, value: float) -> None:
        api_value = int(round(value - 1))
        LOGGER.debug("PortDeviceNumber.async_set_native_value device=%s value=%s api_value=%s", self._device_id, value,
                     api_value)
        from ..api import PortControlApiClient
        client = self.coordinator.entry.runtime_data.client
        assert isinstance(client, PortControlApiClient)
        await client.async_set_device_power_level(self._device_id, api_value)
        await self.coordinator.async_refresh()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


def _sensors_for_device(coordinator: HeaterControlDataUpdateCoordinator, device: dict) -> list:
    return [
        PortDeviceSensor(
            coordinator, device, "hashrateThs", "Hashrate",
            unit="TH/s",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:numeric",
        ),
        PortDeviceSensor(
            coordinator, device, "powerConsumptionW", "Power Consumption",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:flash",
        ),
        PortDeviceSensor(
            coordinator, device, "poolStatus", "Pool Status",
            icon="mdi:connection",
        ),
        PortDeviceSensor(
            coordinator, device, "chipTemperature", "Chip Temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:thermometer",
        ),

    ]


def _switches_for_device(coordinator: HeaterControlDataUpdateCoordinator, device: dict) -> list:
    return [PortDeviceSwitch(coordinator, device)]


def _numbers_for_device(coordinator: HeaterControlDataUpdateCoordinator, device: dict) -> list:
    return [PortDeviceNumber(coordinator, device)]


def _platform_tracked(coordinator: HeaterControlDataUpdateCoordinator, platform: str) -> set[str]:
    """Return a per-platform tracked-device set stored on the coordinator."""
    attr = f"_device_entity_tracked_{platform}"
    if not hasattr(coordinator, attr):
        setattr(coordinator, attr, set())
    return getattr(coordinator, attr)


def _shared_tracked(coordinator: HeaterControlDataUpdateCoordinator) -> set[str]:
    """Return the union of all per-platform tracked sets (used for cleanup)."""
    result: set[str] = set()
    for platform in ("sensors", "switches", "numbers"):
        result |= _platform_tracked(coordinator, platform)
    return result


def _make_dynamic_setup(entity_factory, platform: str):
    """Return a setup function that dynamically registers per-device entities of one platform type."""

    def setup(
            coordinator: HeaterControlDataUpdateCoordinator,
            async_add_entities: AddEntitiesCallback,
            entry: HeaterControlConfigEntry,
    ) -> None:
        tracked = _platform_tracked(coordinator, platform)

        def _handle_update() -> None:
            devices = (coordinator.data or {}).get("devices") or []
            new_devices = [d for d in devices if d["id"] not in tracked]
            if not new_devices:
                return
            new_entities: list = []
            for device in new_devices:
                tracked.add(device["id"])
                new_entities += entity_factory(coordinator, device)
                LOGGER.debug("Registering %s entities for mining device: %s", entity_factory.__name__, device["id"])
            async_add_entities(new_entities)

        _handle_update()
        entry.async_on_unload(coordinator.async_add_listener(_handle_update))

    return setup


setup_dynamic_device_sensors = _make_dynamic_setup(_sensors_for_device, "sensors")
setup_dynamic_device_switches = _make_dynamic_setup(_switches_for_device, "switches")
setup_dynamic_device_numbers = _make_dynamic_setup(_numbers_for_device, "numbers")


def setup_device_cleanup(
        coordinator: HeaterControlDataUpdateCoordinator,
        entry: HeaterControlConfigEntry,
) -> None:
    """Remove entity registry entries for mining devices absent for 2+ hours."""
    hass = coordinator.hass
    removal_cancels: dict[str, callable] = {}

    def _remove_device_entities(device_id: str) -> None:
        registry = er.async_get(hass)
        uid_prefix = f"{coordinator.device}_{device_id}_"
        to_remove = [
            e.entity_id for e in registry.entities.values()
            if (e.unique_id or "").startswith(uid_prefix)
        ]
        for entity_id in to_remove:
            LOGGER.debug("Auto-removing entity %s (device absent for 2h)", entity_id)
            registry.async_remove(entity_id)
        for platform in ("sensors", "switches", "numbers"):
            _platform_tracked(coordinator, platform).discard(device_id)
        removal_cancels.pop(device_id, None)

    def _handle_update() -> None:
        current_ids = {d["id"] for d in (coordinator.data or {}).get("devices") or []}

        # Cancel pending removals for devices that reappeared
        for device_id in list(removal_cancels):
            if device_id in current_ids:
                LOGGER.debug("Mining device %s reappeared, cancelling removal", device_id)
                removal_cancels.pop(device_id)()

        # Schedule removal for newly-disappeared known devices
        tracked = _shared_tracked(coordinator)
        for device_id in tracked - current_ids:
            if device_id not in removal_cancels:
                LOGGER.debug("Mining device %s gone, scheduling removal in 2h", device_id)

                @callback
                def _do_remove(_now, did=device_id):
                    _remove_device_entities(did)

                removal_cancels[device_id] = async_call_later(hass, DEVICE_REMOVAL_DELAY, _do_remove)

    entry.async_on_unload(coordinator.async_add_listener(_handle_update))

    def _cancel_all() -> None:
        for cancel in removal_cancels.values():
            cancel()
        removal_cancels.clear()

    entry.async_on_unload(_cancel_all)
