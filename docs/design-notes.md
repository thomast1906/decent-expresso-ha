# Design notes: data, history and future ideas

Background on how the integration handles data, why, and what could be added later.

## Where data lives

| Data | Stored in | Notes |
|------|-----------|-------|
| Shot history, profiles, beans, grinders, workflow | **Decaid** (the app at e.g. `192.168.0.195:8080`) | The source of truth. Home Assistant never copies or moves it. |
| Latest shot summary | Read from `GET /api/v1/shots/latest` | Shown on the `Last shot` sensor (profile, dose, yield, stop reason). Refreshed every 30 s and whenever a shot, steam, flush or hot-water run finishes. |
| Entity state history | **Home Assistant recorder** (`config/home-assistant_v2.db` by default, or MariaDB/Postgres if `recorder: db_url` is set) | Optional. Default retention is 10 days (`purge_keep_days`). |

The integration keeps nothing on disk. It only holds the latest values in memory.

## How data reaches Home Assistant

- **WebSocket push** (Decaid `ws/v1/...`): `machine/snapshot` (state, temperatures, pressure, flow),
  `machine/waterLevels` and `scale/snapshot`. These send several frames a second and
  reconnect automatically every 10 s if dropped.
- **REST polling every 30 s**: `machine/info`, `machine/state`, `machine/settings`, `workflow`,
  `shots/latest`.
- **Throttling** (`coordinator.py`, `const.py`): entity updates are capped at
  - 1 per second while working (Decaid states `espresso`, `steam`, `hotWater`, `flush`, `steamRinse`, `cleaning`, `descaling`)
  - 1 per 10 seconds otherwise (sleeping, idle, heating)
  - immediately on a machine state change or a WebSocket/scale connect or disconnect.
- Temperatures are rounded to 0.1 °C and pressure/flow to 0.01, so tiny changes don't count as new states.

Measured against a real DE1Pro while it was asleep: before throttling, the group
temperature was recorded about 96 times in 90 s. With the idle throttle and rounding it
was about 8 times in 80 s.

## Current decision: don't save history in Home Assistant

Nothing needs to be saved in HA. The dashboard only uses live values (gauges and tiles, no
`history-graph` cards), so it works with the recorder excluded:

```yaml
# configuration.yaml
recorder:
  exclude:
    entity_globs:
      - "*.decent_espresso_*"
```

**Still works without history:** power switch, buttons, settings, live gauges, last shot,
automations, notifications.

**Lost without history:** entity history and logbook views, history graphs, long-term
statistics (for example daily temperature trends).

## State values

Decaid reports states in camelCase (`hotWater`, `steamRinse`, ...). Home Assistant requires
enum state keys to be lowercase snake_case, so the `State` sensor exposes `hot_water`,
`steam_rinse`, `needs_water`, etc. Use those values in automations and templates.

## Options for later

### A. Keep temperatures only

Useful for warm-up trends and when the machine was on, without storing the fast-changing values:

```yaml
recorder:
  exclude:
    entities:
      - sensor.decent_espresso_pressure
      - sensor.decent_espresso_flow
      - sensor.decent_espresso_scale_weight
      - sensor.decent_espresso_scale_flow
```

### B. Bring back the live extraction graphs

Remove the recorder exclude (or keep only pressure, flow and weight), then add this
section back to `dashboards/decent_espresso.yaml`:

```yaml
      - type: grid
        column_span: 2
        cards:
          - type: heading
            heading: Extraction history
            icon: mdi:chart-line
          - type: history-graph
            hours_to_show: 1
            grid_options:
              columns: full
            entities:
              - entity: sensor.decent_espresso_pressure
                name: Pressure
              - entity: sensor.decent_espresso_flow
                name: Flow
              - entity: sensor.decent_espresso_scale_weight
                name: Weight
          - type: history-graph
            hours_to_show: 6
            grid_options:
              columns: full
            entities:
              - entity: sensor.decent_espresso_group_temperature
                name: Group
              - entity: sensor.decent_espresso_steam_temperature
                name: Steam
```

The 1-second throttle while working gives a coarse extraction curve. For a detailed
per-shot graph, see D.

### C. Keep only the machine state

Enough for a "machine on/off" timeline and to count shots per day, at almost no
storage cost:

```yaml
recorder:
  include:
    entities:
      - sensor.decent_espresso_state
      - sensor.decent_espresso_last_shot
```

Note: a recorder `include` list means *only* those entities are recorded across your
whole HA install, so for an existing setup, excluding the other Decent entities is usually safer.

### D. Per-shot graphs from Decaid (no HA storage)

`GET /api/v1/shots/{id}` returns the full measurements for a shot. A future version
could expose these, for example as an image entity that renders the latest shot's
curve, or through a custom card that queries Decaid directly. The data would then stay
in Decaid and be exact, not throttled.

## Built since

- **Machine ready blueprint** (`blueprints/automation/decent_espresso/machine_ready.yaml`):
  triggers when the power switch is on and group temp >= target minus a margin. A condition
  compares the automation's `last_triggered` with the power switch's `last_changed`, so it
  notifies once per wake-up. Entity inputs are repeated in `trigger_variables` because
  template triggers can't see normal `variables`. Works with the recorder excluded, since
  `last_changed` and `last_triggered` come from the live state machine and restore state.
- **Water section on the dashboard**: tank gauge (max 60 mm is a guess; adjust to your full
  reading), water-low sensor and refill warning level.

- **Plain automation** (`automations/machine_ready.yaml`): the same logic as the blueprint
  with entity IDs hard-coded, for pasting into the automation YAML editor. The trigger fires
  when the "ready" condition changes from false to true, so if the machine is already hot and
  awake when the automation is saved, it waits for the next wake. Toggle power off and on to test.
- **Profile select** (`select.decent_espresso_profile`): options are the titles of visible
  profiles from `GET /api/v1/profiles`. Choosing one sends `PUT /api/v1/workflow` with
  `{"profile": ...}`; Decaid deep-merges it and uploads it to the machine. The list is ~180 KB
  (73 profiles here), so it's polled with `If-None-Match` and Decaid usually replies `304`.
  Shows unknown when the active profile isn't in the library.

## Other ideas not built yet

- **Automations** (plain HA YAML, no code changes needed):
  - Wake at a set time on weekdays: `switch.turn_on` on `switch.decent_espresso_power`.
  - Sleep when everyone leaves home, or after N minutes idle.
  - Notify when `binary_sensor.decent_espresso_water_low` turns on.
  - Notify "shot finished" when `sensor.decent_espresso_last_shot` changes.
- **Shot-settings numbers**: steam temperature/duration, hot water volume/temperature, group
  temperature via `POST /api/v1/machine/shotSettings`.
- **Shot counter / daily stats** from `GET /api/v1/shots` (the source of truth stays in Decaid).
- **Bengle-only features** (cup warmer, LED strip, scale calibration), shown only when
  `GET /api/v1/machine/capabilities` lists them. A plain DE1 returns an empty list.
- **Zeroconf discovery**, if Decaid advertises itself over mDNS.
