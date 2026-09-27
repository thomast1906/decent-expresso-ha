"""Async client for the Decaid REST and WebSocket API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class DecentError(Exception):
    """Base error for the Decent API."""


class DecentConnectionError(DecentError):
    """Decaid could not be reached."""


class DecentApiError(DecentError):
    """Decaid returned an error response."""


class DecentClient:
    """Thin wrapper around the Decaid HTTP API."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._profiles_etag: str | None = None
        self._profiles: list[dict[str, Any]] = []

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        url = f"{self.base_url}/api/v1/{path}"
        try:
            async with self._session.request(
                method, url, json=payload, timeout=REQUEST_TIMEOUT
            ) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise DecentApiError(
                        f"{method} {path} failed ({resp.status}): {_error_detail(text)}"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DecentConnectionError(f"Error talking to Decaid at {url}: {err}") from err
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            return text

    async def get_info(self) -> dict[str, Any]:
        return await self._request("GET", "machine/info")

    async def get_state(self) -> dict[str, Any]:
        return await self._request("GET", "machine/state")

    async def set_state(self, new_state: str) -> None:
        await self._request("PUT", f"machine/state/{new_state}")

    async def get_settings(self) -> dict[str, Any]:
        return await self._request("GET", "machine/settings")

    async def set_settings(self, settings: dict[str, Any]) -> None:
        await self._request("POST", "machine/settings", settings)

    async def set_refill_level(self, level: float) -> None:
        await self._request("POST", "machine/waterLevels", {"refillLevel": level})

    async def get_workflow(self) -> dict[str, Any]:
        return await self._request("GET", "workflow")

    async def set_workflow(self, patch: dict[str, Any]) -> dict[str, Any] | None:
        """Deep-merge ``patch`` into the current workflow; Decaid uploads it to the machine."""
        return await self._request("PUT", "workflow", patch)

    async def get_profiles(self) -> list[dict[str, Any]]:
        """List profiles, using the ETag so unchanged lists (~180 KB) come back as 304."""
        url = f"{self.base_url}/api/v1/profiles"
        headers = {"If-None-Match": self._profiles_etag} if self._profiles_etag else None
        try:
            async with self._session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 304:
                    return self._profiles
                text = await resp.text()
                if resp.status >= 400:
                    raise DecentApiError(
                        f"GET profiles failed ({resp.status}): {_error_detail(text)}"
                    )
                etag = resp.headers.get("ETag")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DecentConnectionError(f"Error talking to Decaid at {url}: {err}") from err
        try:
            profiles = json.loads(text)
        except ValueError as err:
            raise DecentApiError("GET profiles returned invalid JSON") from err
        self._profiles = profiles if isinstance(profiles, list) else []
        self._profiles_etag = etag
        return self._profiles

    async def get_latest_shot(self) -> dict[str, Any] | None:
        try:
            return await self._request("GET", "shots/latest")
        except DecentApiError:
            return None

    async def tare_scale(self) -> None:
        await self._request("PUT", "scale/tare")

    async def listen(
        self,
        channel: str,
        on_message: Callable[[dict[str, Any]], None],
        stop: asyncio.Event,
        reconnect_delay: float,
        on_connection: Callable[[bool], None] | None = None,
    ) -> None:
        """Consume a Decaid WebSocket channel until ``stop`` is set, reconnecting on failure."""
        url = f"ws://{self.host}:{self.port}/ws/v1/{channel}"
        while not stop.is_set():
            try:
                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    _LOGGER.debug("Connected to %s", url)
                    if on_connection:
                        on_connection(True)
                    async for msg in ws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            continue
                        try:
                            data = json.loads(msg.data)
                        except ValueError:
                            continue
                        if isinstance(data, dict):
                            on_message(data)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
                _LOGGER.debug("WebSocket %s error: %s", url, err)
            if on_connection:
                on_connection(False)
            try:
                await asyncio.wait_for(stop.wait(), reconnect_delay)
            except asyncio.TimeoutError:
                pass


def _error_detail(text: str) -> str:
    try:
        body = json.loads(text)
    except ValueError:
        return text or "no body"
    if isinstance(body, dict):
        return str(body.get("error") or body.get("details") or body)
    return str(body)
