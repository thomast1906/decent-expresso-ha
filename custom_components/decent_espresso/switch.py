"""Switches for Decent Espresso: power (wake/sleep) and USB charger."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATE_IDLE, STATE_SLEEPING
from .coordinator import DecentConfigEntry
from .entity import DecentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([DecentPowerSwitch(coordinator), DecentUsbSwitch(coordinator)])


class DecentPowerSwitch(DecentEntity, SwitchEntity):
    """On = awake (any state other than sleeping); off = sleeping."""

    _attr_translation_key = "power"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "power")

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.machine_state
        if state is None:
            return None
        return state != STATE_SLEEPING

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._call(self.coordinator.client.set_state(STATE_IDLE))
        self.coordinator.set_optimistic_state(STATE_IDLE)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._call(self.coordinator.client.set_state(STATE_SLEEPING))
        self.coordinator.set_optimistic_state(STATE_SLEEPING)


class DecentUsbSwitch(DecentEntity, SwitchEntity):
    """USB charger port on the machine."""

    _attr_translation_key = "usb_charger"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "usb_charger")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.settings.get("usb")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._call(self.coordinator.client.set_settings({"usb": "enable"}))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._call(self.coordinator.client.set_settings({"usb": "disable"}))
        await self.coordinator.async_request_refresh()
