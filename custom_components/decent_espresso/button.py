"""Buttons for Decent Espresso machine actions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import DecentClient
from .coordinator import DecentConfigEntry
from .entity import DecentEntity


@dataclass(frozen=True, kw_only=True)
class DecentButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[DecentClient], Awaitable[None]]
    optimistic_state: str | None = None


def _state(new_state: str) -> Callable[[DecentClient], Awaitable[None]]:
    return lambda client: client.set_state(new_state)


BUTTONS: tuple[DecentButtonDescription, ...] = (
    DecentButtonDescription(
        key="stop", translation_key="stop", press_fn=_state("idle"), optimistic_state="idle"
    ),
    DecentButtonDescription(key="flush", translation_key="flush", press_fn=_state("flush")),
    DecentButtonDescription(key="hot_water", translation_key="hot_water", press_fn=_state("hotWater")),
    DecentButtonDescription(key="steam", translation_key="steam", press_fn=_state("steam")),
    # Remote shot start is off by default: only use it when a cup and portafilter are ready.
    DecentButtonDescription(
        key="espresso",
        translation_key="espresso",
        press_fn=_state("espresso"),
        entity_registry_enabled_default=False,
    ),
    DecentButtonDescription(
        key="tare_scale", translation_key="tare_scale", press_fn=lambda c: c.tare_scale()
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DecentButton(coordinator, desc) for desc in BUTTONS)


class DecentButton(DecentEntity, ButtonEntity):
    entity_description: DecentButtonDescription

    def __init__(self, coordinator, description: DecentButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self._call(self.entity_description.press_fn(self.coordinator.client))
        if self.entity_description.optimistic_state:
            self.coordinator.set_optimistic_state(self.entity_description.optimistic_state)
