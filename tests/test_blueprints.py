"""Blueprint tests."""

from pathlib import Path
import shutil

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

BLUEPRINT = Path(__file__).parents[1] / "blueprints/automation/decent_espresso/machine_ready.yaml"

POWER = "switch.decent_espresso_power"
GROUP = "sensor.decent_espresso_group_temperature"
TARGET = "sensor.decent_espresso_target_group_temperature"


async def _setup(hass):
    dest = Path(hass.config.path("blueprints/automation/decent_espresso"))
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(BLUEPRINT, dest / BLUEPRINT.name)
    hass.states.async_set(POWER, "off")
    hass.states.async_set(GROUP, "40")
    hass.states.async_set(TARGET, "91.5")
    calls = async_mock_service(hass, "notify", "test")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "id": "ready",
                "use_blueprint": {
                    "path": "decent_espresso/machine_ready.yaml",
                    "input": {"notify_action": "notify.test"},
                },
            }
        },
    )
    await hass.async_block_till_done()
    return calls


async def _temp(hass, value):
    hass.states.async_set(GROUP, str(value))
    await hass.async_block_till_done()


async def test_notifies_once_per_wake(hass):
    calls = await _setup(hass)

    await _temp(hass, 95)  # hot but asleep
    assert len(calls) == 0

    hass.states.async_set(POWER, "on")
    await _temp(hass, 60)
    await _temp(hass, 85)
    assert len(calls) == 0

    await _temp(hass, 89.6)
    assert len(calls) == 1
    assert calls[0].data["title"] == "Espresso machine ready"
    assert calls[0].data["message"] == "Group head is at 89.6°C (target 91.5°C)."

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
