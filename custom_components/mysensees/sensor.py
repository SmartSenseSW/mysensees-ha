from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MySenseesConfigEntry
from .const import CONF_GATEWAY_ID, DOMAIN
from .coordinator import MySenseesDataUpdateCoordinator

PARTICULATE_UNIT = "\u00b5g/m\u00b3"
SIGNAL_STRENGTH_UNIT = "dBm"


@dataclass(frozen=True, kw_only=True)
class MySenseesSensorDescription(SensorEntityDescription):
    """Describe a MySensees measurement sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    exists_fn: Callable[[dict[str, Any]], bool]


def _find_thing(data: dict[str, Any], sensor_type: str) -> dict[str, Any] | None:
    for thing in data.get("things", []):
        if thing.get("type") == sensor_type:
            return thing
    return None


def _thing_value(data: dict[str, Any], sensor_type: str) -> Any:
    thing = _find_thing(data, sensor_type)
    if not thing:
        return None
    return thing.get("lastMeasurement", {}).get("v")


def _thing_exists(data: dict[str, Any], sensor_type: str) -> bool:
    return _find_thing(data, sensor_type) is not None


def _state_value(data: dict[str, Any], key: str) -> Any:
    return data.get("state", {}).get("deviceState", {}).get(key)


def _state_exists(data: dict[str, Any], key: str) -> bool:
    return key in data.get("state", {}).get("deviceState", {})


def _parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


SENSOR_TYPES: dict[str, MySenseesSensorDescription] = {
    "T": MySenseesSensorDescription(
        key="T",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "T"),
        exists_fn=lambda data: _thing_exists(data, "T"),
    ),
    "RH": MySenseesSensorDescription(
        key="RH",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "RH"),
        exists_fn=lambda data: _thing_exists(data, "RH"),
    ),
    "P": MySenseesSensorDescription(
        key="P",
        name="Pressure",
        native_unit_of_measurement=UnitOfPressure.KPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "P"),
        exists_fn=lambda data: _thing_exists(data, "P"),
    ),
    "CO2": MySenseesSensorDescription(
        key="CO2",
        name="CO2",
        native_unit_of_measurement="ppm",
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "CO2"),
        exists_fn=lambda data: _thing_exists(data, "CO2"),
    ),
    "PM1": MySenseesSensorDescription(
        key="PM1",
        name="PM1",
        native_unit_of_measurement=PARTICULATE_UNIT,
        device_class=SensorDeviceClass.PM1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "PM1"),
        exists_fn=lambda data: _thing_exists(data, "PM1"),
    ),
    "PM2.5": MySenseesSensorDescription(
        key="PM2.5",
        name="PM2.5",
        native_unit_of_measurement=PARTICULATE_UNIT,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "PM2.5"),
        exists_fn=lambda data: _thing_exists(data, "PM2.5"),
    ),
    "PM10": MySenseesSensorDescription(
        key="PM10",
        name="PM10",
        native_unit_of_measurement=PARTICULATE_UNIT,
        device_class=SensorDeviceClass.PM10,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _thing_value(data, "PM10"),
        exists_fn=lambda data: _thing_exists(data, "PM10"),
    ),
}

DIAGNOSTIC_SENSORS: tuple[MySenseesSensorDescription, ...] = (
    MySenseesSensorDescription(
        key="wifiRSSI",
        name="WiFi RSSI",
        native_unit_of_measurement=SIGNAL_STRENGTH_UNIT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _state_value(data, "wifiRSSI"),
        exists_fn=lambda data: _state_exists(data, "wifiRSSI"),
    ),
    MySenseesSensorDescription(
        key="uptime",
        name="Uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _state_value(data, "uptime"),
        exists_fn=lambda data: _state_exists(data, "uptime"),
    ),
    MySenseesSensorDescription(
        key="LDSR",
        name="Last Seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _parse_timestamp(_state_value(data, "LDSR")),
        exists_fn=lambda data: _state_exists(data, "LDSR"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MySenseesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MySensees sensors."""
    coordinator: MySenseesDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_sensor_types: set[str] = set()

    @callback
    def async_add_missing_entities() -> None:
        data = coordinator.data
        entities: list[MySenseesSensor] = []

        for sensor_type, description in SENSOR_TYPES.items():
            if sensor_type in known_sensor_types or not description.exists_fn(data):
                continue
            known_sensor_types.add(sensor_type)
            entities.append(MySenseesSensor(coordinator, entry, description, sensor_type))

        for description in DIAGNOSTIC_SENSORS:
            if description.key in known_sensor_types or not description.exists_fn(data):
                continue
            known_sensor_types.add(description.key)
            entities.append(
                MySenseesSensor(coordinator, entry, description, description.key)
            )

        if entities:
            async_add_entities(entities)

    async_add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_missing_entities))


class MySenseesSensor(
    CoordinatorEntity[MySenseesDataUpdateCoordinator], SensorEntity
):
    """Representation of a MySensees sensor."""

    entity_description: MySenseesSensorDescription

    def __init__(
        self,
        coordinator: MySenseesDataUpdateCoordinator,
        entry: MySenseesConfigEntry,
        description: MySenseesSensorDescription,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._gateway_id = entry.data[CONF_GATEWAY_ID]
        self._attr_unique_id = f"{self._gateway_id}_{sensor_type}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for this gateway."""
        data = self.coordinator.data
        editable = data.get("editable", {})
        inventory = data.get("inventory", {})

        return {
            "identifiers": {(DOMAIN, self._gateway_id)},
            "name": editable.get("name") or self._gateway_id,
            "model": inventory.get("hw_ver"),
            "sw_version": inventory.get("sw_ver"),
            "serial_number": inventory.get("S/N"),
        }
