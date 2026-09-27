"""Constants for the Decent Espresso integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "decent_espresso"

DEFAULT_PORT = 8080
DEFAULT_NAME = "Decent Espresso"

# REST polling for slow-changing data (info, settings, workflow, last shot).
SCAN_INTERVAL = timedelta(seconds=30)
# Live WebSocket frames arrive several times a second; entity writes are throttled,
# fast while the machine is working and slower otherwise to spare the recorder.
LIVE_UPDATE_THROTTLE_ACTIVE = 1.0
LIVE_UPDATE_THROTTLE_IDLE = 10.0
ACTIVE_STATES = {"espresso", "steam", "hotWater", "flush", "steamRinse", "cleaning", "descaling"}
WS_RECONNECT_DELAY = 10

STATE_SLEEPING = "sleeping"
STATE_IDLE = "idle"

MACHINE_STATES = [
    "booting",
    "busy",
    "idle",
    "sleeping",
    "heating",
    "preheating",
    "espresso",
    "hotWater",
    "flush",
    "steam",
    "steamRinse",
    "skipStep",
    "cleaning",
    "descaling",
    "calibration",
    "selfTest",
    "airPurge",
    "needsWater",
    "error",
    "fwUpgrade",
]
