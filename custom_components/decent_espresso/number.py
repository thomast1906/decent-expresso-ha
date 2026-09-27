"""Numbers for Decent Espresso machine settings."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import DecentClient
from .coordinator import DecentConfigEntry, DecentData
from .entity import DecentEntity


@dataclass(frozen=True, kw_only=True)
class DecentNumberDescription(NumberEntityDescription):
    value_fn: Callable[[DecentData], Any]
    set_fn: Callable[[DecentClient, float], Awaitable[None]]


def _setting(key: str, cast: type = float) -> dict[str, Any]:
    return {
        "value_fn": lambda d: d.settings.get(key),
        "set_fn": lambda c, v: c.set_settings({key: cast(v)}),
    }


FLOW = {
    "device_class": NumberDeviceClass.VOLUME_FLOW_RATE,
    "native_unit_of_measurement": UnitOfVolumeFlowRate.MILLILITERS_PER_SECOND,
}

NUMBERS: tuple[DecentNumberDescription, ...] = (
    DecentNumberDescription(
        key="steam_flow", translation_key="steam_flow",
        native_min_value=0.4, native_max_value=2.5, native_step=0.1,
        **FLOW, **_setting("steamFlow"),
    ),
    DecentNumberDescription(
        key="hot_water_flow", translation_key="hot_water_flow",
        native_min_value=1, native_max_value=10, native_step=0.5,
        **FLOW, **_setting("hotWaterFlow"),
    ),
    DecentNumberDescription(
        key="flush_flow", translation_key="flush_flow",
        native_min_value=1, native_max_value=10, native_step=0.5,
        **FLOW, **_setting("flushFlow"),
    ),
    DecentNumberDescription(
        key="flush_temperature", translation_key="flush_temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=60, native_max_value=100, native_step=1,
        **_setting("flushTemp", int),
    ),
    DecentNumberDescription(
        key="flush_timeout", translation_key="flush_timeout",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=1, native_max_value=60, native_step=1,
        **_setting("flushTimeout", int),
    ),
    DecentNumberDescription(
        key="fan_threshold", translation_key="fan_threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0, native_max_value=60, native_step=1,
        entity_category=EntityCategory.CONFIG,
        **_setting("fan", int),
    ),
    DecentNumberDescription(
        key="refill_level", translation_key="refill_level",
        device_class=NumberDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        native_min_value=0, native_max_value=70, native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: d.water.get("refillLevel"),
        set_fn=lambda c, v: c.set_refill_level(int(v)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DecentNumber(coordinator, desc) for desc in NUMBERS)


class DecentNumber(DecentEntity, NumberEntity):
    entity_description: DecentNumberDescription
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, description: DecentNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        await self._call(self.entity_description.set_fn(self.coordinator.client, value))
        await self.coordinator.async_request_refresh()
