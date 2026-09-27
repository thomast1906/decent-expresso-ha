"""Binary sensors for Decent Espresso."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DecentConfigEntry, DecentData
from .entity import DecentEntity


def _water_low(d: DecentData) -> bool | None:
    current, refill = d.water.get("currentLevel"), d.water.get("refillLevel")
    if current is None or refill is None:
        return None
    return current <= refill


@dataclass(frozen=True, kw_only=True)
class DecentBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[DecentData], bool | None]


BINARY_SENSORS: tuple[DecentBinarySensorDescription, ...] = (
    DecentBinarySensorDescription(
        key="water_low",
        translation_key="water_low",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_water_low,
    ),
    DecentBinarySensorDescription(
        key="scale_connected",
        translation_key="scale_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.scale_connected,
    ),
    DecentBinarySensorDescription(
        key="live_updates",
        translation_key="live_updates",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.live_connected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    # Plumbed machines with a refill kit always read "low", so skip that sensor there.
    refill_kit = (coordinator.data.info.get("extra") or {}).get("refillKit")
    async_add_entities(
        DecentBinarySensor(coordinator, desc)
        for desc in BINARY_SENSORS
        if not (desc.key == "water_low" and refill_kit)
    )


class DecentBinarySensor(DecentEntity, BinarySensorEntity):
    entity_description: DecentBinarySensorDescription

    def __init__(self, coordinator, description: DecentBinarySensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
