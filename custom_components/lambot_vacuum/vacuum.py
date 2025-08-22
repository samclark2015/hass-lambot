"""Support for MQTT vacuums."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from core.homeassistant.components.mqtt.entity import CONF_ENABLED_BY_DEFAULT
from core.homeassistant.const import CONF_ENTITY_CATEGORY
from homeassistant.components.mqtt import (
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    MQTT_RW_SCHEMA,
    subscription,
)
from homeassistant.components.mqtt.entity import MqttEntity
from homeassistant.components.vacuum import StateVacuumEntity, VacuumEntityFeature
from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import json_dumps
from homeassistant.util.json import json_loads_object

if TYPE_CHECKING:
    from homeassistant.components.mqtt.models import ReceiveMessage
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import VolSchemaType

    from .data import LambotConfigEntry

LAMBOT_STATUS = 16
type LambotCommand = VacuumEntityFeature | Literal["RESUME"]

PAYLOADS: dict[LambotCommand, Any] = {
    VacuumEntityFeature.RETURN_HOME: {"f": 25},
    VacuumEntityFeature.START: {"f": 26},
    VacuumEntityFeature.PAUSE: {"f": 24, "p": 1},
    "RESUME": {"f": 24, "p": 2},
}

STATES: dict[int, VacuumActivity] = {
    0: VacuumActivity.IDLE,
    1: VacuumActivity.DOCKED,
    2: VacuumActivity.DOCKED,
    3: VacuumActivity.DOCKED,
    4: VacuumActivity.RETURNING,
    5: VacuumActivity.RETURNING,
    6: VacuumActivity.CLEANING,
    7: VacuumActivity.PAUSED,
    8: VacuumActivity.CLEANING,
    9: VacuumActivity.CLEANING,
    11: VacuumActivity.CLEANING,
    12: VacuumActivity.PAUSED,
    13: VacuumActivity.PAUSED,
    14: VacuumActivity.CLEANING,
    15: VacuumActivity.PAUSED,
    16: VacuumActivity.CLEANING,
    17: VacuumActivity.PAUSED,
    18: VacuumActivity.CLEANING,
    19: VacuumActivity.PAUSED,
    20: VacuumActivity.CLEANING,
    21: VacuumActivity.PAUSED,
    22: VacuumActivity.CLEANING,
    23: VacuumActivity.PAUSED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LambotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MQTT vacuum through YAML and through MQTT discovery."""
    async_add_entities(
        [
            LambotVacuum(
                hass,
                config_entry,
            )
        ]
    )


class LambotVacuum(MqttEntity, StateVacuumEntity):
    """Representation of a MQTT-controlled state vacuum."""

    _config_entry: LambotConfigEntry
    _default_name = "Lambot Vacuum"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: LambotConfigEntry,
    ) -> None:
        config = MQTT_RW_SCHEMA(
            {
                CONF_STATE_TOPIC: config_entry.runtime_data.app_topic,
                CONF_COMMAND_TOPIC: config_entry.runtime_data.robot_topic,
                CONF_ENABLED_BY_DEFAULT: True,
            }
        )
        MqttEntity.__init__(self, hass, config, config_entry, None)

    @staticmethod
    def config_schema() -> VolSchemaType:
        """Return the config schema."""
        return MQTT_RW_SCHEMA

    @callback
    def _state_message_received(self, msg: ReceiveMessage) -> None:
        """Handle state MQTT message."""
        payload = json_loads_object(msg.payload)
        if "f" in payload and payload["f"] == LAMBOT_STATUS:
            state = payload.get("p")
            if isinstance(state, int):
                self._attr_state = STATES.get(state, STATE_UNKNOWN)
                self.async_write_ha_state()

    @callback
    def _prepare_subscribe_topics(self) -> None:
        """(Re)Subscribe to topics."""
        self.add_subscription(
            CONF_STATE_TOPIC,
            self._state_message_received,
            {"_attr_state"},
        )

    async def _subscribe_topics(self) -> None:
        """(Re)Subscribe to topics."""
        subscription.async_subscribe_topics_internal(self.hass, self._sub_state)

    async def _async_publish_command(self, feature: LambotCommand) -> None:
        """Publish a command."""
        await self.async_publish_with_config(
            self._config_entry.runtime_data.robot_topic, json_dumps(PAYLOADS[feature])
        )
        self.async_write_ha_state()

    async def async_start(self) -> None:
        """Start the vacuum."""
        await self._async_publish_command(VacuumEntityFeature.START)

    async def async_pause(self) -> None:
        """Pause the vacuum."""
        await self._async_publish_command(VacuumEntityFeature.PAUSE)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum."""
        await self._async_publish_command(VacuumEntityFeature.STOP)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Tell the vacuum to return to its dock."""
        await self._async_publish_command(VacuumEntityFeature.RETURN_HOME)

    # async def async_clean_spot(self, **kwargs: Any) -> None:
    #     """Perform a spot clean-up."""
    #     await self._async_publish_command(VacuumEntityFeature.CLEAN_SPOT)

    # async def async_locate(self, **kwargs: Any) -> None:
    #     """Locate the vacuum (usually by playing a song)."""
    #     await self._async_publish_command(VacuumEntityFeature.LOCATE)

    # async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
    #     """Set fan speed."""
    #     if (
    #         self._set_fan_speed_topic is None
    #         or (self.supported_features & VacuumEntityFeature.FAN_SPEED == 0)
    #         or (fan_speed not in self.fan_speed_list)
    #     ):
    #         return
    #     await self.async_publish_with_config(self._set_fan_speed_topic, fan_speed)

    # async def async_send_command(
    #     self,
    #     command: str,
    #     params: dict[str, Any] | list[Any] | None = None,
    #     **kwargs: Any,
    # ) -> None:
    #     """Send a command to a vacuum cleaner."""
    #     if (
    #         self._send_command_topic is None
    #         or self.supported_features & VacuumEntityFeature.SEND_COMMAND == 0
    #     ):
    #         return
    #     if isinstance(params, dict):
    #         message: dict[str, Any] = {"command": command}
    #         message.update(params)
    #         payload = json_dumps(message)
    #     else:
    #         payload = command
    #     await self.async_publish_with_config(self._send_command_topic, payload)
    #     else:
    #         payload = command
    #     await self.async_publish_with_config(self._send_command_topic, payload)
