"""Config flow for AQUAmatrix SMASVFX integration with MFA support."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SMASVFXClient
from .const import CONF_PASSWORD, CONF_TENANT, CONF_USERNAME, DEFAULT_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TENANT, default="SMASVFX"): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class SMASVFXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AQUAmatrix SMASVFX."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}
        self.client: SMASVFXClient | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial credential step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            session = async_get_clientsession(self.hass)
            tenant = user_input[CONF_TENANT].strip("/")
            
            self.client = SMASVFXClient(
                session,
                DEFAULT_BASE_URL,
                tenant,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                _LOGGER,
            )

            try:
                result = await self.client.login()
                if result == "mfa_required":
                    return await self.async_step_mfa()
                elif result == "success":
                    await self.async_set_unique_id(f"{tenant}:{user_input[CONF_USERNAME]}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"AQUAmatrix ({tenant})", data=user_input
                    )
            except Exception as err:
                _LOGGER.exception("Login failed:


                                  
