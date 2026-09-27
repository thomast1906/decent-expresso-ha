# Decent Espresso for Home Assistant

A Home Assistant custom integration for Decent espresso machines. It talks to the
[Decaid](https://github.com/decentespresso/decaid) app's local API on port 8080
(see its [API reference](https://github.com/decentespresso/decaid/blob/main/doc/Api.md)).

- **Local push**: machine state, temperatures, pressure, flow, water level and scale
  weight stream over Decaid's WebSockets. Home Assistant updates about once a second
  while the machine is working, and every 10 seconds otherwise.
- **REST polling** every 30 s picks up machine info, settings, the active profile and
  the latest shot.

## Installation

### HACS (custom repository)

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thomast1906&repository=decent-expresso-ha&category=integration)

The button opens HACS on your Home Assistant with this repository ready to add as a
custom repository. Download **Decent Espresso**, then restart Home Assistant.

Or add it by hand: HACS → **⋮** (top right) → **Custom repositories** → add
`https://github.com/thomast1906/decent-expresso-ha`, type **Integration**.

### Manual

Copy `custom_components/decent_espresso` into your Home Assistant `config/custom_components/`
folder and restart.

## Setup

[![Open your Home Assistant instance and start setting up Decent Espresso.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=decent_espresso)

Or go to **Settings → Devices & services → Add integration → Decent Espresso**. Enter the
IP address of the device running Decaid (for example `192.168.0.195`) and port `8080`.

## Entities

| Type | Entities |
|------|----------|
| Switch | **Power** (on = `PUT /machine/state/idle`, off = `PUT /machine/state/sleeping`), USB charger |
| Button | Stop (back to idle), Flush, Hot water, Steam, Tare scale, Start espresso *(disabled by default)* |
| Sensor | State, substate, group/mix/steam temperature, target group/mix temperature, pressure, flow, water level, scale weight/flow/battery, profile, target dose/yield, last shot (with profile, dose, yield, stop reason attributes), firmware |
| Binary sensor | Water low (hidden on machines with a refill kit), scale connected, live updates |
| Select | **Profile**: lists Decaid's visible profiles; choosing one applies it via `PUT /api/v1/workflow` |
| Number | Steam flow, hot water flow, flush flow/temperature/duration, fan threshold, refill warning level |

Power in an automation:

```yaml
action: switch.turn_on
target:
  entity_id: switch.decent_espresso_power
```

## Dashboard

[`dashboards/decent_espresso.yaml`](dashboards/decent_espresso.yaml) is a ready-made
sections dashboard with a power toggle, a profile dropdown, machine state, a water tank gauge, temperature gauges, action
buttons, live pressure/flow/weight gauges, the last shot and settings. It only shows
live values, so it doesn't need any history saved in Home Assistant.

1. **Settings → Dashboards → Add dashboard → New dashboard from scratch**.
2. Open it, then **⋮ → Edit dashboard → ⋮ → Raw configuration editor**.
3. Paste the file contents and save.

## Notifications

There are two ways to get a "machine ready" notification when the group head reaches its target
temperature (within 2 °C) after the machine wakes. Both notify once per wake-up. Pick one.

### Option 1: plain automation (paste YAML)

1. **Settings → Automations & scenes → Create automation → Create new automation**.
2. **⋮** (top right) → **Edit in YAML**, and paste
   [`automations/machine_ready.yaml`](automations/machine_ready.yaml).
3. **Change the notify action.** Replace `notify.mobile_app_your_phone` with your phone's action.
   Install the Home Assistant Companion app, then find the name under **Developer tools → Actions**
   by typing `notify.mobile_app` (e.g. `notify.mobile_app_johns_iphone`).
4. Save, then **⋮ → Run actions** to send a test notification.

### Option 2: blueprint

[`blueprints/automation/decent_espresso/machine_ready.yaml`](blueprints/automation/decent_espresso/machine_ready.yaml)
does the same, with the margin, notify action and message as form fields instead of YAML.

[![Open your Home Assistant instance and show the blueprint import dialog with this blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthomast1906%2Fdecent-expresso-ha%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fdecent_espresso%2Fmachine_ready.yaml)

Or import it with **Settings → Automations & scenes → Blueprints → Import blueprint** using:

```
https://github.com/thomast1906/decent-expresso-ha/blob/main/blueprints/automation/decent_espresso/machine_ready.yaml
```

Importing only adds the blueprint. Then open it under **Blueprints → Create automation**,
set **Notify action** to your phone (e.g. `notify.mobile_app_your_phone`) and save. For manual installs, copy the file to
`config/blueprints/automation/decent_espresso/` and reload automations.

## History (optional)

Nothing needs to be stored in Home Assistant: live values come from Decaid, and your
shot history and profiles stay in Decaid. To keep these entities out of the Home
Assistant database entirely, add this to `configuration.yaml` and restart:

```yaml
recorder:
  exclude:
    entity_globs:
      - "*.decent_espresso_*"
```

Entity history and logbook views will then be empty; the dashboard, controls and
automations keep working. See [`docs/design-notes.md`](docs/design-notes.md) for other
history options and ideas for later.

## Development

```bash
uv venv -p 3.13 .venv
uv pip install -p .venv -r requirements_test.txt
.venv/bin/pytest -q
```
