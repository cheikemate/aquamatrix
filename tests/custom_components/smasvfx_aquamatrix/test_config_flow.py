"""Test config flow for AQUAmatrix SMASVFX."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.smasvfx_aquamatrix.const import DOMAIN


async def test_user_flow(hass: HomeAssistant, mock_smasvfx_client) -> None:
    """Test the user step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.smasvfx_aquamatrix.config_flow.validate_input",
        return_value={"title": "AQUAmatrix (SMASVFX)", "tenant": "SMASVFX"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "tenant": "SMASVFX",
                "username": "test-user",
                "password": "test-password",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "AQUAmatrix (SMASVFX)"
    assert result["data"] == {
        "tenant": "SMSnet",
        "username": "test-user",
        "password": "test-password",
    }
