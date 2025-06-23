"""Custom types for 21energy_heater_control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import HeaterControlApiClient
    from .coordinator import HeaterControlDataUpdateCoordinator


type HeaterControlConfigEntry = ConfigEntry[HeaterControlData]


@dataclass
class HeaterControlData:
    """Data for the integration."""

    client: HeaterControlApiClient
    coordinator: HeaterControlDataUpdateCoordinator
    integration: Integration