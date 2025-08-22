"""
Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_DEVICE_ID, CONF_PREFIX, Platform
from homeassistant.loader import async_get_loaded_integration

from .data import LambotData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import LambotConfigEntry

PLATFORMS: list[Platform] = [Platform.VACUUM]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: LambotConfigEntry,
) -> bool:
    device_id = entry.data.get(CONF_DEVICE_ID)
    topic_prefix = entry.data.get(CONF_PREFIX, "")
    if topic_prefix and topic_prefix[-1] != "/":
        topic_prefix = topic_prefix + "/"

    """Set up this integration using UI."""
    entry.runtime_data = LambotData(
        integration=async_get_loaded_integration(hass, entry.domain),
        app_topic=topic_prefix + "device/" + device_id + "/app",
        robot_topic=topic_prefix + "device/" + device_id + "/robot",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: LambotConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: LambotConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
