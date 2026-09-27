"""Sensors for Decent Espresso."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfMass,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import MACHINE_STATES, STATE_OPTIONS, state_key
from .coordinator import DecentConfigEntry, DecentData
from .entity import DecentEntity


@dataclass(frozen=True, kw_only=True)
class DecentSensorDescription(SensorEntityDescription):
    value_fn: Callable[[DecentData], Any]
    attrs_fn: Callable[[DecentData], dict[str, Any] | None] | None = None


def _snap(key: str, digits: int | None = None) -> Callable[[DecentData], Any]:
    if digits is None:
        return lambda d: d.snapshot.get(key)
    return lambda d: _round(d.snapshot.get(key), digits)


def _round(value: Any, digits: int = 1) -> Any:
    return round(value, digits) if isinstance(value, (int, float)) else value


def _profile(d: DecentData) -> dict[str, Any]:
    return d.workflow.get("profile") or {}


def _context(d: DecentData) -> dict[str, Any]:
    return d.workflow.get("context") or {}


def _shot_time(d: DecentData) -> datetime | None:
    shot = d.latest_shot or {}
    raw = shot.get("createdAt") or shot.get("timestamp")
    if not raw:
        return None
    parsed = dt_util.parse_datetime(raw)
    if parsed and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return parsed


def _shot_attrs(d: DecentData) -> dict[str, Any] | None:
    shot = d.latest_shot
    if not shot:
        return None
    workflow = shot.get("workflow") or {}
    context = workflow.get("context") or {}
    annotations = shot.get("annotations") or {}
    return {
        "shot_id": shot.get("id"),
        "profile": (workflow.get("profile") or {}).get("title"),
        "target_dose": context.get("targetDoseWeight"),
        "target_yield": context.get("targetYield"),
        "actual_dose": annotations.get("actualDoseWeight"),
        "actual_yield": annotations.get("actualYield"),
        "stop_reason": shot.get("stopReason"),
    }


TEMP = {
    "device_class": SensorDeviceClass.TEMPERATURE,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    "state_class": SensorStateClass.MEASUREMENT,
    "suggested_display_precision": 1,
}

SENSORS: tuple[DecentSensorDescription, ...] = (
    DecentSensorDescription(
        key="state",
        translation_key="state",
        device_class=SensorDeviceClass.ENUM,
        options=STATE_OPTIONS,
        value_fn=lambda d: state_key(d.machine_state) if d.machine_state in MACHINE_STATES else None,
    ),
    DecentSensorDescription(
        key="substate",
        translation_key="substate",
        value_fn=lambda d: d.machine_substate,
    ),
    DecentSensorDescription(
        key="group_temperature", translation_key="group_temperature",
        value_fn=_snap("groupTemperature", 1), **TEMP,
    ),
    DecentSensorDescription(
        key="mix_temperature", translation_key="mix_temperature",
        value_fn=_snap("mixTemperature", 1), **TEMP,
    ),
    DecentSensorDescription(
        key="steam_temperature", translation_key="steam_temperature",
        value_fn=_snap("steamTemperature", 1), **TEMP,
    ),
    DecentSensorDescription(
        key="target_group_temperature", translation_key="target_group_temperature",
        value_fn=_snap("targetGroupTemperature"), **TEMP,
    ),
    DecentSensorDescription(
        key="target_mix_temperature", translation_key="target_mix_temperature",
        value_fn=_snap("targetMixTemperature"), entity_registry_enabled_default=False, **TEMP,
    ),
    DecentSensorDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _round(d.snapshot.get("pressure"), 2),
    ),
    DecentSensorDescription(
        key="target_pressure",
        translation_key="target_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_snap("targetPressure"),
    ),
    DecentSensorDescription(
        key="flow",
        translation_key="flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.MILLILITERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _round(d.snapshot.get("flow"), 2),
    ),
    DecentSensorDescription(
        key="target_flow",
        translation_key="target_flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.MILLILITERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_snap("targetFlow"),
    ),
    DecentSensorDescription(
        key="profile_frame",
        translation_key="profile_frame",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_snap("profileFrame"),
    ),
    DecentSensorDescription(
        key="water_level",
        translation_key="water_level",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: _round(d.water.get("currentLevel")),
    ),
    DecentSensorDescription(
        key="scale_weight",
        translation_key="scale_weight",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _round(d.scale.get("weight")) if d.scale_connected else None,
    ),
    DecentSensorDescription(
        key="scale_flow",
        translation_key="scale_flow",
        native_unit_of_measurement="g/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _round(d.scale.get("weightFlow")) if d.scale_connected else None,
    ),
    DecentSensorDescription(
        key="scale_battery",
        translation_key="scale_battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.scale.get("battery") if d.scale_connected else None,
    ),
    DecentSensorDescription(
        key="profile",
        translation_key="profile",
        value_fn=lambda d: _profile(d).get("title"),
        attrs_fn=lambda d: {
            "author": _profile(d).get("author"),
            "notes": _profile(d).get("notes"),
            "beverage_type": _profile(d).get("beverage_type"),
        },
    ),
    DecentSensorDescription(
        key="target_dose",
        translation_key="target_dose",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        value_fn=lambda d: _context(d).get("targetDoseWeight"),
    ),
    DecentSensorDescription(
        key="target_yield",
        translation_key="target_yield",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        value_fn=lambda d: _context(d).get("targetYield"),
    ),
    DecentSensorDescription(
        key="last_shot",
        translation_key="last_shot",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_shot_time,
        attrs_fn=_shot_attrs,
    ),
    DecentSensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.info.get("version"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DecentSensor(coordinator, desc) for desc in SENSORS)


class DecentSensor(DecentEntity, SensorEntity):
    entity_description: DecentSensorDescription

    def __init__(self, coordinator, description: DecentSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
