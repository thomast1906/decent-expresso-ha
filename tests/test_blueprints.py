"""Blueprint tests."""

from pathlib import Path
import shutil

import yaml

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

ROOT = Path(__file__).parents[1]
BLUEPRINT = ROOT / "blueprints/automation/decent_espresso/machine_ready.yaml"
AUTOMATION = ROOT / "automations/machine_ready.yaml"

POWER = "switch.decent_espresso_power"
GROUP = "sensor.decent_espresso_group_temperature"
TARGET = "sensor.decent_espresso_target_group_temperature"


async def _setup(hass, plain: bool = False):
    dest = Path(hass.config.path("blueprints/automation/decent_espresso"))
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(BLUEPRINT, dest / BLUEPRINT.name)
    hass.states.async_set(POWER, "off")
    hass.states.async_set(GROUP, "40")
    hass.states.async_set(TARGET, "91.5")
    if plain:
        config = yaml.safe_load(AUTOMATION.read_text())
        config["id"] = "ready"
        calls = async_mock_service(hass, "notify", "mobile_app_your_phone")
    else:
        config = {
            "id": "ready",
            "use_blueprint": {
                "path": "decent_espresso/machine_ready.yaml",
                "input": {"notify_action": "notify.test"},
            },
        }
        calls = async_mock_service(hass, "notify", "test")
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()
    return calls


async def _temp(hass, value):
    hass.states.async_set(GROUP, str(value))
    await hass.async_block_till_done()


import pytest


@pytest.mark.parametrize("plain", [False, True], ids=["blueprint", "plain_automation"])
async def test_notifies_once_per_wake(hass, plain):
    calls = await _setup(hass, plain)

    await _temp(hass, 95)  # hot but asleep
    assert len(calls) == 0

    hass.states.async_set(POWER, "on")
    await _temp(hass, 60)
    await _temp(hass, 85)
    assert len(calls) == 0

    await _temp(hass, 89.6)
    assert len(calls) == 1
    assert " ".join(calls[0].data["message"].split()) == (
        "Decent Espresso ready, group head at 89.6°C (target 91.5°C)."
    )

    # Dip during a shot then recover: no repeat.
    await _temp(hass, 80)
    await _temp(hass, 91)
    assert len(calls) == 1

    # Sleep and wake again: notifies again.
    hass.states.async_set(POWER, "off")
    await _temp(hass, 70)
    hass.states.async_set(POWER, "on")
    await hass.async_block_till_done()
    await _temp(hass, 90)
    assert len(calls) == 2
