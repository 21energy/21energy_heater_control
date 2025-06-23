"""Constants for 21energy_heater_control."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "21energy_heater_control"
TITLE = "21energy Heater Control"
MANUFACTURER = "21energy"

CONF_POLLING_INTERVAL = "polling_interval"
DEVICE_CLASS_ENUM = "enum"
STATE_ON = "on"
STATE_OFF = "off"