"""Config flow for 21energy_heater_control integration."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import HeaterControlApiClientAuthenticationError, HeaterControlApiClientCommunicationError, \
    HeaterControlApiClientOutdatedError, PortControlApiClient
from .const import CONF_DEVICE_TYPE, CONF_POLLING_INTERVAL, DEVICE_TYPE_OFEN, DEVICE_TYPE_PORT, DOMAIN, LOGGER
from .device_registry import DEVICE_REGISTRY, create_client


def _load_device_type_options() -> list[dict[str, str]]:
    """Read strings.json once at import time (synchronous, before event loop starts)."""
    strings = json.loads((pathlib.Path(__file__).parent / "strings.json").read_text())
    labels: dict[str, str] = strings["selector"]["device_type"]["options"]
    return [{"value": k, "label": labels[k]} for k in DEVICE_REGISTRY if k in labels]


_DEVICE_TYPE_OPTIONS = _load_device_type_options()

STEP_CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_POLLING_INTERVAL, default=30): int,
    }
)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""


class WrongDeviceType(exceptions.HomeAssistantError):
    """Error to indicate the device at the host is not the selected device type."""


class UnpairedError(exceptions.HomeAssistantError):
    """Error to indicate the device is not paired."""


class HeaterControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 21energy_heater_control."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize flow."""
        self._host: str | None = None
        self._interval: int | None = None
        self._device_type: str | None = None

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: select device type."""
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_connection()

        schema = vol.Schema({
            vol.Required(CONF_DEVICE_TYPE): SelectSelector(
                SelectSelectorConfig(
                    options=_DEVICE_TYPE_OPTIONS,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_connection(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: enter host and polling interval, then validate."""
        errors = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._interval = user_input[CONF_POLLING_INTERVAL]
            LOGGER.debug("async_step_connection => _host:%s _device_type:%s", self._host, self._device_type)

            try:
                info = await self._validate_and_setup()
                LOGGER.debug("async_step_connection => info:%s", info)
            except UnpairedError:
                errors["base"] = "unpaired"
            except WrongDeviceType:
                errors["base"] = "wrong_device_type"
            except (CannotConnect, HeaterControlApiClientCommunicationError):
                errors["base"] = "cannot_connect"
            except InvalidHost:
                errors["host"] = "cannot_connect"
            except HeaterControlApiClientOutdatedError:
                errors["base"] = "outdated"
            except HeaterControlApiClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception as e:
                LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"
            else:
                # Network calls succeeded — flow management outside try/except
                await self.async_set_unique_id(info["product_id"])
                self._abort_if_unique_id_configured()

                entry_data = {
                    CONF_HOST: self._host,
                    CONF_POLLING_INTERVAL: self._interval,
                    CONF_DEVICE_TYPE: info[CONF_DEVICE_TYPE],
                    "model": info["model"],
                    "version": info["version"],
                    "product_id": info["product_id"],
                    "pool_config": info.get("pool_config"),
                }
                if self._device_type == DEVICE_TYPE_PORT:
                    entry_data["device_name"] = info.get("device_name", "21PORT")

                title = info.get("device_name") or f"{info['model']} ({info['product_id']})"
                return self.async_create_entry(title=title, data=entry_data)

        return self.async_show_form(
            step_id="connection",
            data_schema=STEP_CONNECTION_SCHEMA,
            errors=errors,
        )

    async def _validate_and_setup(self) -> dict:
        """Validate the host and return device info dict."""
        if len(self._host) < 3:
            LOGGER.error("Invalid hostname %s!", self._host)
            raise InvalidHost

        session = async_get_clientsession(self.hass)
        client = create_client(
            {CONF_HOST: self._host, CONF_DEVICE_TYPE: self._device_type},
            session,
        )

        if not await client.async_get_status():
            LOGGER.error("Could not connect to %s!", self._host)
            raise CannotConnect

        device = await client.async_get_device()

        if self._device_type == DEVICE_TYPE_PORT:
            if device.get("model") != "21PORT":
                raise WrongDeviceType
            assert isinstance(client, PortControlApiClient)
            return {
                CONF_DEVICE_TYPE: DEVICE_TYPE_PORT,
                "model": device["model"],
                "version": device["version"],
                "product_id": self._host,
                "device_name": device.get("device_name", "21PORT"),
                "is_paired": True,
                "pool_config": None,
            }
        else:  # DEVICE_TYPE_OFEN
            if not device.get("is_paired"):
                raise UnpairedError
            if not device.get("product_id"):
                raise CannotConnect
            pool_config = await client.async_get_poolConfig()
            device[CONF_DEVICE_TYPE] = DEVICE_TYPE_OFEN
            device["pool_config"] = pool_config
            return device
