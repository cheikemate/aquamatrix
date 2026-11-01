"""Test config flow for AQUAmatrix SMASVFX."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.smasvfx_aquamatrix.const import DOMAIN


async def test_user_flow(hass: HomeAssistant, mock_smsnet_client) -> None:
    """Test the user step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.smasvfx_aquamatrix.config_flow.SMASVFXClient",
        return_value=mock_smsnet_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "tenant": "SMASVFX",
                "username": "209642718",
                "password": "test-password",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "AQUAmatrix (SMASVFX)"
    assert result["data"] == {
        "tenant": "SMASVFX",
        "username": "209642718",
        "password": "test-password",
    }


