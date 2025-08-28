"""Adds config flow for Blueprint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from homeassistant import config_entries

from .const import DOMAIN, LAMBOT_MDNS_PARTS, LOGGER

if TYPE_CHECKING:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

ZEROCONF_SERVICE = "._lambot._tcp.local."


class LambotFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle Zeroconf discovery."""
        name = discovery_info.name.removesuffix(ZEROCONF_SERVICE)
        parts = name.split("_")

        if len(parts) != LAMBOT_MDNS_PARTS or (parts[0] != "LB" and parts[1] != "VA"):
            LOGGER.error("Unexpected Zeroconf discovery name: %s", name)
            return self.async_abort(
                reason=f"Unexpected Zeroconf discovery name: {name}"
            )

        uuid_str = parts[-1]

        uuid = UUID(uuid_str)
        hostname = discovery_info.hostname
        port = discovery_info.port

        config_data = {
            "uuid": uuid,
            "ip": hostname,
            "port": port,
        }

        await self.async_set_unique_id(str(uuid))
        self._abort_if_unique_id_configured(updates=config_data)

        return self.async_create_entry(
            title=name,
            data=config_data,
        )
