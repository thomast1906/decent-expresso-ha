"""Shared fixtures."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.decent_espresso.const import DOMAIN

HOST = "192.168.0.195"
BASE = f"http://{HOST}:8080/api/v1"

INFO = {"version": "1333", "model": "DE1Pro", "serialNumber": "12614", "GHC": True,
        "extra": {"refillKit": False, "voltage": 220}}
STATE = {"timestamp": "2026-09-27T10:47:31.808758", "state": {"state": "sleeping", "substate": "idle"},
         "flow": 0.0, "pressure": 0.0034, "targetFlow": 6.0, "targetPressure": 0.0,
         "mixTemperature": 56.32, "groupTemperature": 57.02, "targetMixTemperature": 90.0,
         "targetGroupTemperature": 91.5, "profileFrame": 4, "steamTemperature": 126}
SETTINGS = {"fan": 50, "usb": True, "flushTemp": 90.0, "flushTimeout": 6.0, "flushFlow": 6.0,
            "hotWaterFlow": 8.0, "steamFlow": 1.8, "tankTemp": 0, "steamPurgeMode": 0}
WORKFLOW = {"profile": {"title": "Default", "author": "Decent"},
            "context": {"targetDoseWeight": 18.0, "targetYield": 36.0}}
SHOT = {"id": "ec06", "createdAt": "2026-09-27T09:12:12.354751Z",
        "workflow": {"profile": {"title": "Default"}, "context": {"targetDoseWeight": 18.0}},
        "annotations": {"actualDoseWeight": 18.0}, "stopReason": "machineEnded"}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def no_websockets():
    """Replace the WebSocket listener with one that idles until stopped."""

    async def _listen(self, channel, on_message, stop, reconnect_delay, on_connection=None):
        await stop.wait()

    with patch("custom_components.decent_espresso.api.DecentClient.listen", _listen):
        yield


@pytest.fixture
def mock_api(aioclient_mock):
    aioclient_mock.get(f"{BASE}/machine/info", json=INFO)
    aioclient_mock.get(f"{BASE}/machine/state", json=STATE)
    aioclient_mock.get(f"{BASE}/machine/settings", json=SETTINGS)
    aioclient_mock.get(f"{BASE}/workflow", json=WORKFLOW)
    aioclient_mock.get(f"{BASE}/shots/latest", json=SHOT)
    aioclient_mock.put(f"{BASE}/machine/state/idle")
    aioclient_mock.put(f"{BASE}/machine/state/sleeping")
    aioclient_mock.post(f"{BASE}/machine/settings", status=202)
    return aioclient_mock


@pytest.fixture
def config_entry():
    return MockConfigEntry(domain=DOMAIN, unique_id="12614", title="Decent Espresso DE1Pro",
                           data={"host": HOST, "port": 8080})


@pytest.fixture
async def setup_integration(hass, mock_api, config_entry):
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    yield config_entry
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
