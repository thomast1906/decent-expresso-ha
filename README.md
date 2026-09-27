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

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/thomast1906/decent-expresso-ha`, category **Integration**.
2. Install **Decent Espresso** and restart Home Assistant.

### Manual

Copy `custom_components/decent_espresso` into your Home Assistant `config/custom_components/`
folder and restart.

## Setup

**Settings → Devices & services → Add integration → Decent Espresso**, then enter the
IP address of the device running Decaid (for example `192.168.0.195`) and port `8080`.

## Entities

| Type | Entities |
|------|----------|
| Switch | **Power** (on = `PUT /machine/state/idle`, off = `PUT /machine/state/sleeping`), USB charger |
| Button | Stop (back to idle), Flush, Hot water, Steam, Tare scale, Start espresso *(disabled by default)* |
| Sensor | State, substate, group/mix/steam temperature, target group/mix temperature, pressure, flow, water level, scale weight/flow/battery, profile, target dose/yield, last shot (with profile, dose, yield, stop reason attributes), firmware |
| Binary sensor | Water low (hidden on machines with a refill kit), scale connected, live updates |
| Number | Steam flow, hot water flow, flush flow/temperature/duration, fan threshold, refill warning level |

Power in an automation:

```yaml
action: switch.turn_on
target:
  entity_id: switch.decent_espresso_power
```

## Dashboard

[`dashboards/decent_espresso.yaml`](dashboards/decent_espresso.yaml) is a ready-made
sections dashboard with a power toggle, machine state, temperature gauges, action
buttons, live pressure/flow/weight graphs, the last shot and settings.

1. **Settings → Dashboards → Add dashboard → New dashboard from scratch**.
2. Open it, then **⋮ → Edit dashboard → ⋮ → Raw configuration editor**.
3. Paste the file contents and save.

## Development

```bash
uv venv -p 3.13 .venv
uv pip install -p .venv -r requirements_test.txt
.venv/bin/pytest -q
```
