"""The AQUAmatrix SMSnet integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SMSNetClient
from .const import (
    CONF_PASSWORD,
    CONF_TENANT,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SMSNetCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AQUAmatrix SMSnet from a config entry."""
    session = async_get_clientsession(hass)
    tenant = entry.data[CONF_TENANT]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    base_url = DEFAULT_BASE_URL

    client = SMSNetClient(session, base_url, tenant, username, password, _LOGGER)
    coordinator = SMSNetCoordinator(hass, client, logger=_LOGGER)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
