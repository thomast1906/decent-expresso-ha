"""Data coordinator combining REST polling with live WebSocket updates."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DecentClient, DecentError
from .const import (
    ACTIVE_STATES,
    DOMAIN,
    LIVE_UPDATE_THROTTLE_ACTIVE,
    LIVE_UPDATE_THROTTLE_IDLE,
    SCAN_INTERVAL,
    WS_RECONNECT_DELAY,
)

_LOGGER = logging.getLogger(__name__)

type DecentConfigEntry = ConfigEntry[DecentCoordinator]


@dataclass
class DecentData:
    """Everything the entities read from."""

    info: dict[str, Any] = field(default_factory=dict)
    snapshot: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    workflow: dict[str, Any] = field(default_factory=dict)
    latest_shot: dict[str, Any] | None = None
    water: dict[str, Any] = field(default_factory=dict)
    scale: dict[str, Any] = field(default_factory=dict)
    scale_connected: bool = False
    live_connected: bool = False

    @property
    def machine_state(self) -> str | None:
        return (self.snapshot.get("state") or {}).get("state")

    @property
    def machine_substate(self) -> str | None:
        return (self.snapshot.get("state") or {}).get("substate")


class DecentCoordinator(DataUpdateCoordinator[DecentData]):
    """Polls slow data over REST and streams machine/water/scale data over WebSocket."""

    config_entry: DecentConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: DecentConfigEntry, client: DecentClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self._live = DecentData()
        self._stop = asyncio.Event()
        self._last_push = 0.0
        self._pending_push: CALLBACK_TYPE | None = None

    async def _async_update_data(self) -> DecentData:
        try:
            info, snapshot, settings, workflow, shot = await asyncio.gather(
                self.client.get_info(),
                self.client.get_state(),
                self.client.get_settings(),
                self.client.get_workflow(),
                self.client.get_latest_shot(),
            )
        except DecentError as err:
            raise UpdateFailed(str(err)) from err
        data = self._live
        data.info = info or {}
        if not data.live_connected:
            data.snapshot = snapshot or {}
        data.settings = settings or {}
        data.workflow = workflow or {}
        data.latest_shot = shot
        return data

    @callback
    def start_live_updates(self) -> None:
        """Spawn WebSocket listeners bound to the config entry lifecycle."""
        entry = self.config_entry
        for channel, handler in (
            ("machine/snapshot", self._on_snapshot),
            ("machine/waterLevels", self._on_water),
            ("scale/snapshot", self._on_scale),
        ):
            entry.async_create_background_task(
                self.hass,
                self.client.listen(
                    channel,
                    handler,
                    self._stop,
                    WS_RECONNECT_DELAY,
                    self._on_ws_connection if channel == "machine/snapshot" else None,
                ),
                f"{DOMAIN}_{channel}",
            )

    async def async_shutdown(self) -> None:
        self._stop.set()
        if self._pending_push:
            self._pending_push()
            self._pending_push = None
        await super().async_shutdown()

    @callback
    def _on_ws_connection(self, connected: bool) -> None:
        self._live.live_connected = connected
        self._push(force=True)

    @callback
    def _on_snapshot(self, msg: dict[str, Any]) -> None:
        previous = self._live.machine_state
        self._live.snapshot = msg
        changed = self._live.machine_state != previous
        self._push(force=changed)
        if changed and previous in ACTIVE_STATES:
            # A shot/steam just finished; pick up the new record.
            self.hass.async_create_task(self.async_request_refresh())

    @callback
    def _on_water(self, msg: dict[str, Any]) -> None:
        self._live.water = msg
        self._push()

    @callback
    def _on_scale(self, msg: dict[str, Any]) -> None:
        if "status" in msg:
            self._live.scale_connected = msg["status"] == "connected"
            if not self._live.scale_connected:
                self._live.scale = {}
            self._push(force=True)
            return
        self._live.scale_connected = True
        self._live.scale = msg
        self._push()

    @callback
    def set_optimistic_state(self, state: str) -> None:
        snapshot = dict(self._live.snapshot)
        snapshot["state"] = {**(snapshot.get("state") or {}), "state": state}
        self._live.snapshot = snapshot
        self._push(force=True)

    @callback
    def _push(self, force: bool = False) -> None:
        """Notify entities, throttled so high-rate frames don't flood the recorder."""
        if self.data is None:
            return
        throttle = (
            LIVE_UPDATE_THROTTLE_ACTIVE
            if self._live.machine_state in ACTIVE_STATES
            else LIVE_UPDATE_THROTTLE_IDLE
        )
        now = time.monotonic()
        if force or now - self._last_push >= throttle:
            if self._pending_push:
                self._pending_push()
                self._pending_push = None
            self._last_push = now
            self.async_update_listeners()
        elif self._pending_push is None:
            delay = throttle - (now - self._last_push)
            self._pending_push = async_call_later(self.hass, delay, self._delayed_push)

    @callback
    def _delayed_push(self, _now: Any) -> None:
        self._pending_push = None
        self._last_push = time.monotonic()
        self.async_update_listeners()
