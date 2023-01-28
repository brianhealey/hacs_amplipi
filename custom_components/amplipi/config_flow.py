"""Config flow for AmpliPi."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import async_timeout
import voluptuous as vol
from aiohttp import ClientError, ClientSession
from homeassistant import config_entries, exceptions, data_entry_flow
from homeassistant.components import zeroconf
from homeassistant.const import CONF_ID, CONF_NAME, CONF_PORT, CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import DiscoveryInfoType
from pyamplipi.amplipi import AmpliPi

from .const import DOMAIN, CONF_VENDOR, CONF_VERSION, CONF_WEBAPP, CONF_API_PATH

_LOGGER = logging.getLogger(__name__)


async def async_retrieve_info(hass, host, port):
    """Validate the user input allows us to connect."""
    session: ClientSession = async_get_clientsession(hass)

    _LOGGER.info("Attempting to retrieve AmpliPi details")

    try:
        with async_timeout.timeout(5000):
            client = AmpliPi(
                f"http://{host}:{port}/api/",
                10,
                session
            )
            return await client.get_status()

    except ClientError as err:
        _LOGGER.error("Error connecting to AmpliPi Controller: %s ", err, exc_info=True)
        raise
    except asyncio.TimeoutError:
        _LOGGER.error("Timed out when connecting to AmpliPi Controller")
        raise


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AmpliPi."""

    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self._controller_hostname: str | None = None
        self._controller_port: int | None = None
        self._name: str | None = None
        self._uuid: str | None = None
        self._vendor: str | None = None
        self._version: str | None = None
        self._webapp_url: str | None = None
        self._api_path: str | None = None

    @callback
    def _async_get_entry(self):
        return self.async_create_entry(
            title=self._name,
            description="AmpliPi Multizone Media Controller",
            data={
                CONF_NAME: self._name,
                CONF_HOST: self._controller_hostname,
                CONF_PORT: self._controller_port,
                CONF_ID: self._uuid,
                CONF_VENDOR: self._vendor,
                CONF_VERSION: self._version,
                CONF_WEBAPP: self._webapp_url,
                CONF_API_PATH: self._api_path,
            },
        )

    async def _set_uid_and_abort(self):
        await self.async_set_unique_id(self._uuid)
        self._abort_if_unique_id_configured(
            updates={
                CONF_NAME: self._name,
                CONF_HOST: self._controller_hostname,
                CONF_PORT: self._controller_port,
                CONF_VENDOR: self._vendor,
                CONF_VERSION: self._version,
                CONF_WEBAPP: self._webapp_url,
                CONF_API_PATH: self._api_path,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        return await self.async_step_user_confirm(user_input)

    async def async_step_user_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        _LOGGER.warning("New Amplipi by user")
        errors = {}
        if user_input is not None:
            # noinspection PyBroadException
            try:
                await async_retrieve_info(self.hass, user_input[CONF_HOST], user_input[CONF_PORT])

                self._controller_hostname = user_input[CONF_HOST]
                self._controller_port = user_input[CONF_PORT]
                self._name = "AmpliPi"
                self._vendor = "Unknown"
                self._version = "Unknown"
                self._uuid = ""  # this is not right.  we need a uuid
                self._webapp_url = f"http://${user_input[CONF_HOST]}"
                self._api_path = f"/api"

                return self._async_get_entry()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    description="The hostname of the AmpliPi Controller",
                    default=self._controller_hostname,
                ): str,
                vol.Required(
                    CONF_PORT,
                    description="The port for the api endpoints",
                    default=self._controller_port,
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                CONF_VENDOR: self._vendor,
                CONF_VERSION: self._version
            }
        )

    async def async_step_zeroconf(self, discovery_info: zeroconf.ZeroconfServiceInfo):
        """Handle zeroconf discovery."""
        _LOGGER.info("discovered %s", discovery_info)
        self._controller_hostname = discovery_info.host
        self._controller_port = discovery_info.port
        self._name = discovery_info.properties['name']
        self._vendor = discovery_info.properties['vendor']
        self._version = discovery_info.properties['version']
        self._uuid = discovery_info.name
        self._webapp_url = discovery_info.properties['web_app']
        self._api_path = discovery_info.properties['path']

        await self._set_uid_and_abort()

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None):
        """Handle user-confirmation of discovered node."""
        errors = {}
        if user_input is not None:
            # noinspection PyBroadException
            try:
                await async_retrieve_info(self.hass, self._controller_hostname, self._controller_port)
                return self._async_get_entry()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    description="The hostname of the AmpliPi Controller",
                    default=self._controller_hostname,
                ): str,
                vol.Required(
                    CONF_PORT,
                    description="The port for the api endpoints",
                    default=self._controller_port,
                ): int,
            }
        )

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                CONF_VENDOR: self._vendor,
                CONF_VERSION: self._version
            }
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
