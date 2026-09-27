"""Entity behaviour tests."""

from datetime import timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .conftest import BASE


async def test_sensors(hass, setup_integration):
    assert hass.states.get("sensor.decent_espresso_state").state == "sleeping"
    assert float(hass.states.get("sensor.decent_espresso_group_temperature").state) == 57.0
    assert hass.states.get("sensor.decent_espresso_profile").state == "Default"
    assert hass.states.get("sensor.decent_espresso_target_yield").state == "36.0"
    last_shot = hass.states.get("sensor.decent_espresso_last_shot")
    assert last_shot.state.startswith("2026-09-27T09:12:12")
    assert last_shot.attributes["stop_reason"] == "machineEnded"
    assert hass.states.get("switch.decent_espresso_power").state == "off"
    assert hass.states.get("switch.decent_espresso_usb_charger").state == "on"
    assert float(hass.states.get("number.decent_espresso_steam_flow").state) == 1.8


async def test_power_switch(hass, setup_integration, mock_api):
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.decent_espresso_power"}, blocking=True)
    assert any(str(c[1]).endswith("/machine/state/idle") and c[0] == "PUT" for c in mock_api.mock_calls)
    assert hass.states.get("switch.decent_espresso_power").state == "on"

    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.decent_espresso_power"}, blocking=True)
    assert any(str(c[1]).endswith("/machine/state/sleeping") and c[0] == "PUT" for c in mock_api.mock_calls)
    assert hass.states.get("switch.decent_espresso_power").state == "off"


async def test_number_posts_setting(hass, setup_integration, mock_api):
    await hass.services.async_call(
        "number", "set_value", {"entity_id": "number.decent_espresso_steam_flow", "value": 1.2}, blocking=True
    )
    posts = [c for c in mock_api.mock_calls if c[0] == "POST" and str(c[1]).endswith("/machine/settings")]
    assert posts[-1][2] == {"steamFlow": 1.2}


async def test_live_updates(hass, setup_integration):
    coordinator = setup_integration.runtime_data
    coordinator._on_ws_connection(True)
    coordinator._on_water({"currentLevel": 4.0, "refillLevel": 5.0})
    coordinator._on_scale({"status": "connected"})
    snapshot = {"state": {"state": "espresso", "substate": "pouring"}, "pressure": 8.9, "flow": 2.1}
    coordinator._on_snapshot(snapshot)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.decent_espresso_state").state == "espresso"
    assert hass.states.get("sensor.decent_espresso_pressure").state == "8.9"
    assert hass.states.get("binary_sensor.decent_espresso_water_low").state == "on"
    assert hass.states.get("binary_sensor.decent_espresso_live_updates").state == "on"

    # Rapid non-state frames are throttled, then flushed.
    coordinator._on_scale({"weight": 20.5, "weightFlow": 1.9, "battery": 80})
    coordinator._on_snapshot({**snapshot, "pressure": 9.1})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()
    assert hass.states.get("sensor.decent_espresso_pressure").state == "9.1"
    assert hass.states.get("sensor.decent_espresso_scale_weight").state == "20.5"


async def test_setup_retries_when_unreachable(hass, aioclient_mock, config_entry):
    aioclient_mock.get(f"{BASE}/machine/info", exc=TimeoutError())
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state.name == "SETUP_RETRY"


async def test_camel_case_state_maps_to_snake_case(hass, setup_integration):
    coordinator = setup_integration.runtime_data
    coordinator._on_snapshot({"state": {"state": "hotWater", "substate": "pouring"}})
    await hass.async_block_till_done()
    state = hass.states.get("sensor.decent_espresso_state")
    assert state.state == "hot_water"
    assert "hot_water" in state.attributes["options"]
