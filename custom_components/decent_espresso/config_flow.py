"""Config flow for Decent Espresso."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DecentClient, DecentError
from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class DecentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the Decaid host and port."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = DecentClient(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_PORT],
            )
            try:
                info = await client.get_info()
            except DecentError:
                errors["base"] = "cannot_connect"
            else:
                serial = (info or {}).get("serialNumber")
                unique_id = serial or f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(str(unique_id))
                self._abort_if_unique_id_configured(updates=user_input)
                model = (info or {}).get("model")
                title = f"{DEFAULT_NAME} {model}" if model else DEFAULT_NAME
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
