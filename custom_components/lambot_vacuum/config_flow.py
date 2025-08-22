"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from core.homeassistant.const import CONF_DEVICE_ID, CONF_FRIENDLY_NAME, CONF_PREFIX
from homeassistant import config_entries
from homeassistant.components import mqtt
from slugify import slugify

from .const import DOMAIN, LOGGER


class LambotFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        # Make sure MQTT integration is enabled and the client is available
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            LOGGER.error("MQTT integration is not available")
            return self.async_abort(reason="MQTT integration is not available")

        _errors = {}
        if user_input is not None:
            await self.async_set_unique_id(
                unique_id=slugify(user_input[CONF_DEVICE_ID])
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(
                    CONF_FRIENDLY_NAME, f"Lambot {user_input[CONF_DEVICE_ID]}"
                ),
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_ID,
                        default=(user_input or {}).get(CONF_DEVICE_ID, vol.UNDEFINED),
                        description="Lambot Device ID",
                    ): str,
                    vol.Optional(
                        CONF_FRIENDLY_NAME,
                        default=(user_input or {}).get(CONF_FRIENDLY_NAME, None),
                        description="Nickname for the device",
                    ): str,
                    vol.Optional(
                        CONF_PREFIX,
                        default=(user_input or {}).get(CONF_PREFIX, vol.UNDEFINED),
                        description="MQTT topic prefix",
                    ): str,
                },
            ),
            errors=_errors,
        )