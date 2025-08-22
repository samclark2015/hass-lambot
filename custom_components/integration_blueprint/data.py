"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration


type LambotConfigEntry = ConfigEntry[LambotData]


@dataclass
class LambotData:
    """Data for the Blueprint integration."""

    integration: Integration
    robot_topic: str
    app_topic: str
