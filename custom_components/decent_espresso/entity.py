"""Base entity for Decent Espresso."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import DecentError
from .const import DEFAULT_NAME, DOMAIN
from .coordinator import DecentCoordinator


class DecentEntity(CoordinatorEntity[DecentCoordinator]):
    """Common device info and unique IDs."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DecentCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        info = coordinator.data.info
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Decent Espresso",
            model=info.get("model"),
            serial_number=info.get("serialNumber"),
            sw_version=info.get("version"),
            configuration_url=f"{coordinator.client.base_url}",
        )

    async def _call(self, awaitable: Awaitable) -> None:
        try:
            await awaitable
        except DecentError as err:
            raise HomeAssistantError(str(err)) from err
