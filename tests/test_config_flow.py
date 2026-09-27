"""Config flow tests."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.decent_espresso.const import DOMAIN

from .conftest import BASE, HOST


async def test_user_flow_success(hass, mock_api):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": HOST, "port": 8080})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Decent Espresso DE1Pro"
    assert result["result"].unique_id == "12614"


async def test_user_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/machine/info", exc=TimeoutError())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": HOST, "port": 8080})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(hass, mock_api, config_entry):
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": HOST, "port": 8080})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
