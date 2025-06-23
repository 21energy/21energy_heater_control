"""Config flow for 21energy_heater_control integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (DOMAIN, CONF_POLLING_INTERVAL, LOGGER)
from .api import HeaterControlApiClient

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_POLLING_INTERVAL, default=60): int,
    })

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
    
# This is the schema that used to display the UI to the user. This simple
# schema has a single required host field, but it could include a number of fields
# such as username, password etc. See other components in the HA core code for
# further examples.
# Note the input displayed to the user will be translated. See the
# translations/<lang>.json file and strings.json. See here for further information:
# https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#translations
# At the time of writing I found the translations created by the scaffold didn't
# quite work as documented and always gave me the "Lokalise key references" string
# (in square brackets), rather than the actual translated value. I did not attempt to
# figure this out or look further into it.

class HeaterControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 21energy_heater_control."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize flow."""
        self._host: str | None = None
        self._interval: int | None = None

    async def _async_step_user_base(self, user_input: dict[str, Any] | None = None, error: str | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        info = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._interval = user_input[CONF_POLLING_INTERVAL]
            LOGGER.debug(f"_async_step_user_base => _host:{self._host}")
            LOGGER.debug(f"_async_step_user_base => _interval:{self._interval}")

            try:
                info = await self._validate_and_setup()
                if "device" in info:
                    await self.async_set_unique_id(info["device"])
                    self._abort_if_unique_id_configured(updates=user_input)
                    user_input["device"] = info["device"]
                    user_input["model"] = info["model"]
                    user_input["app_version"] = info["app_version"]
                    user_input["pool_username"] = info["pool_username"]
                return self.async_create_entry(title=f"{info["model"]} ({info["device"]})", data=user_input)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                errors["host"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return await self._async_step_user_base(user_input=user_input)

    async def _validate_and_setup(self) -> dict:
        """Validate the host allows us to connect.
        Return the device
        """
        # Validate the data can be used to set up a connection.

        if len(self._host) < 3:
            LOGGER.exception(
                "Invalid hostname %s!", self._host
            )
            raise InvalidHost

        client = HeaterControlApiClient(
            host=self._host,
            session=async_get_clientsession(self.hass),
        )
        result = {}
        if not await client.async_get_status():
            # If there is an error, raise an exception to notify HA that there was a
            # problem. The UI will also show there was a problem
            LOGGER.exception(
                "Could not connect to %s!", self._host
            )
            raise CannotConnect
        else:
            result = await client.async_get_device()
        return result

