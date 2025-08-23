"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "lambot_vacuum"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

LAMBOT_MQTT_USERNAME = "Lambot"
LAMBOT_MQTT_PASSWORD = "lambot123"  # noqa: S105
LAMBOT_OP_STATUS = 16
LAMBOT_MDNS_PARTS = 5
LAMBOT_STATUS_WAIT = 10