"""The AmpliPi integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyamplipi.amplipi import AmpliPi

from .const import DOMAIN, AMPLIPI_OBJECT, CONF_VENDOR, CONF_VERSION

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["media_player"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AmpliPi from a config entry."""
    # TODO Store an API object for your platforms to access
    # data = {
    #            CONF_NAME: self._name,
    #            CONF_HOST: self._controller_hostname,
    #            CONF_PORT: self._controller_port,
    #            CONF_ID: self._uuid,
    #            CONF_VENDOR: self._vendor,
    #            CONF_VERSION: self._version
    #        },

    hostname = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        AMPLIPI_OBJECT: AmpliPi(
            f'http://{hostname}:{port}/api',
            10,
            http_session=async_get_clientsession(hass)
        ),
        CONF_VENDOR: entry.data[CONF_VENDOR],
        CONF_NAME: entry.data[CONF_NAME],
        CONF_HOST: entry.data[CONF_HOST],
        CONF_PORT: entry.data[CONF_PORT],
        CONF_ID: entry.data[CONF_ID],
        CONF_VERSION: entry.data[CONF_VERSION],
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
