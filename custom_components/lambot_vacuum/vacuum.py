"""Support for MQTT vacuums."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from aiomqtt import Client, Message
from homeassistant.components.vacuum import StateVacuumEntity, VacuumEntityFeature
from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.helpers.json import json_dumps
from homeassistant.util.json import json_loads_object
from pytz import UTC

from .const import (
    LAMBOT_MQTT_PASSWORD,
    LAMBOT_MQTT_USERNAME,
    LAMBOT_OP_STATUS,
    LAMBOT_STATUS_WAIT,
    LOGGER,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import LambotConfigEntry

type LambotCommand = Literal["RESUME", "STATUS"] | VacuumEntityFeature

PAYLOADS: dict[LambotCommand, Any] = {
    VacuumEntityFeature.RETURN_HOME: {"f": 25},
    VacuumEntityFeature.START: {"f": 26},
    VacuumEntityFeature.PAUSE: {"f": 24, "p": 1},
    "RESUME": {"f": 24, "p": 2},
    "STATUS": {"f": 41},
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


class LambotVacuum(StateVacuumEntity):
    """Class representing a Lambot vacuum cleaner."""

    def __init__(self, hass: HomeAssistant, config_entry: LambotConfigEntry) -> None:
        """Create a new instance."""
        super().__init__()
        self._hass = hass
        self._config_entry = config_entry
        self._read_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._last_status_timestamp: datetime | None = None
        self._client = Client(
            config_entry.runtime_data.address,
            config_entry.runtime_data.port,
            username=LAMBOT_MQTT_USERNAME,
            password=LAMBOT_MQTT_PASSWORD,
        )

        uuid = str(config_entry.runtime_data.uuid)
        self._attr_unique_id = uuid
        self._command_topic = f"device/{uuid}/robot"
        self._state_topic = f"device/{uuid}/app"

        for feature in PAYLOADS:
            if isinstance(feature, VacuumEntityFeature):
                self._attr_supported_features |= feature

    async def _heartbeat(self) -> None:
        while True:
            if self._last_status_timestamp is None or self._last_status_timestamp < (
                datetime.now(tz=UTC) - timedelta(seconds=LAMBOT_STATUS_WAIT)
            ):
                await self._async_publish_command("STATUS")
                LOGGER.info("Heartbeat: requesting status update")
            await asyncio.sleep(LAMBOT_STATUS_WAIT)

    async def _process_messages(self) -> None:
        async for message in self._client.messages:
            await self._handle_message(message)

    async def _handle_message(self, msg: Message) -> None:
        if not isinstance(msg.payload, (bytes, bytearray, str, memoryview)):
            return

        payload = json_loads_object(msg.payload)
        if "f" in payload and payload["f"] == LAMBOT_OP_STATUS:
            state = payload.get("p")
            if isinstance(state, int):
                self._attr_activity = STATES.get(state)
                self._last_status_timestamp = datetime.now(tz=UTC)
                self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle when the entity is added to Home Assistant."""
        await self._client.__aenter__()
        if not self._read_task:
            self._read_task = self._config_entry.async_create_background_task(
                self._hass, self._process_messages(), "LambotVacuumRead"
            )
        if not self._heartbeat_task:
            self._heartbeat_task = self._config_entry.async_create_background_task(
                self._hass, self._heartbeat(), "LambotVacuumHeartbeat"
            )
        await self._client.subscribe(self._state_topic)

    async def async_will_remove_from_hass(self) -> None:
        """Handle when the entity is removed from Home Assistant."""
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        await self._client.unsubscribe(self._state_topic)
        await self._client.__aexit__(None, None, None)

    async def _async_publish_command(self, feature: LambotCommand) -> None:
        """Publish a command to the MQTT broker."""
        topic = self._command_topic
        payload = json_dumps(PAYLOADS[feature])
        await self._client.publish(topic, payload)

    async def async_start(self) -> None:
        """Start the vacuum."""
        if self.activity == VacuumActivity.PAUSED:
            await self._async_publish_command("RESUME")
        else:
            await self._async_publish_command(VacuumEntityFeature.START)

    async def async_pause(self) -> None:
        """Pause the vacuum."""
        await self._async_publish_command(VacuumEntityFeature.PAUSE)

    async def async_stop(self, **_kwargs: Any) -> None:
        """Stop the vacuum."""
        await self._async_publish_command(VacuumEntityFeature.STOP)

    async def async_return_to_base(self, **_kwargs: Any) -> None:
        """Tell the vacuum to return to its dock."""
        await self._async_publish_command(VacuumEntityFeature.RETURN_HOME)
