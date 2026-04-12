"""Config flow for AQUAmatrix SMSnet integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SMSNetClient
from .const import CONF_PASSWORD, CONF_TENANT, CONF_USERNAME, DEFAULT_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TENANT, default="SMSnet"): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    tenant = data[CONF_TENANT].strip("/")
    client = SMSNetClient(
        session,
        DEFAULT_BASE_URL,
        tenant,
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        _LOGGER,
    )

    try:
        await client.login_basic()
    except Exception as err:
        _LOGGER.exception("Login failed: %s", err)
        raise Exception("cannot_connect") from err

    return {"title": f"AQUAmatrix ({tenant})", "tenant": tenant}


class SMSNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AQUAmatrix SMSnet."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(f"{info['tenant']}:{user_input[CONF_USERNAME]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML."""
        tenant = import_data.get(CONF_TENANT, "SMSnet").strip("/")
        username = import_data.get(CONF_USERNAME, "")
        await self.async_set_unique_id(f"{tenant}:{username}")
        self._abort_if_unique_id_configured()
        return await self.async_step_user(import_data)

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> SMSNetOptionsFlowHandler:
        """Get the options flow for this handler."""
        return SMSNetOptionsFlowHandler()


class SMSNetOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle AQUAmatrix SMSnet options."""

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
