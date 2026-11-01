"""Config flow for AQUAmatrix SMASVFX integration with MFA support."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
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
                _LOGGER.exception("Login failed: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def async_step_mfa(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the MFA verification code step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            code = user_input["verification_code"]
            assert self.client is not None  # Satisfies Mypy type check
            try:
                success = await self.client.verify_mfa(code)
                if success:
                    tenant = self.data[CONF_TENANT].strip("/")
                    username = self.data[CONF_USERNAME]
                    await self.async_set_unique_id(f"{tenant}:{username}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"AQUAmatrix ({tenant})", data=self.data
                    )
                else:
                    errors["base"] = "invalid_mfa_code"
            except Exception as err:
                _LOGGER.exception("MFA verification failed: %s", err)
                errors["base"] = "invalid_mfa_code"

        schema = vol.Schema(
            {
                vol.Required("verification_code"): str,
            }
        )
        return self.async_show_form(
            step_id="mfa",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML."""
        tenant = import_data.get(CONF_TENANT, "SMASVFX").strip("/")
        username = import_data.get(CONF_USERNAME, "")
        await self.async_set_unique_id(f"{tenant}:{username}")
        self._abort_if_unique_id_configured()
        return await self.async_step_user(import_data)

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> SMASVFXOptionsFlowHandler:
        """Get the options flow for this handler."""
        return SMASVFXOptionsFlowHandler()


class SMASVFXOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle AQUAmatrix SMASVFX options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=self.config_entry.data.get(CONF_USERNAME),
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=self.config_entry.data.get(CONF_PASSWORD),
                    ): str,
                }
            ),
        )


