"""Profile select for Decent Espresso."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DecentConfigEntry
from .entity import DecentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DecentProfileSelect(entry.runtime_data)])


class DecentProfileSelect(DecentEntity, SelectEntity):
    """Pick the active Decaid profile; applied via PUT /api/v1/workflow."""

    _attr_translation_key = "profile_select"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "profile_select")

    def _visible_profiles(self) -> dict[str, dict[str, Any]]:
        by_title: dict[str, dict[str, Any]] = {}
        for record in self.coordinator.data.profiles:
            profile = record.get("profile") or {}
            title = profile.get("title")
            if title and record.get("visibility", "visible") == "visible":
                by_title.setdefault(title, profile)
        return dict(sorted(by_title.items(), key=lambda item: item[0].casefold()))

    @property
    def options(self) -> list[str]:
        return list(self._visible_profiles())

    @property
    def current_option(self) -> str | None:
        # None (unknown) when the active profile isn't in Decaid's library, e.g. an unsaved edit.
        title = (self.coordinator.data.workflow.get("profile") or {}).get("title")
        return title if title in self._visible_profiles() else None

    async def async_select_option(self, option: str) -> None:
        profile = self._visible_profiles().get(option)
        if profile is None:
            raise ServiceValidationError(f"Unknown profile: {option}")
        workflow = await self._call_result(
            self.coordinator.client.set_workflow({"profile": profile})
        )
        if isinstance(workflow, dict) and workflow.get("profile"):
            self.coordinator.set_optimistic_workflow(workflow)
        else:
            self.coordinator.set_optimistic_workflow(
                {**self.coordinator.data.workflow, "profile": profile}
            )
