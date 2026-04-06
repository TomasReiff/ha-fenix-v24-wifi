"""Config flow for Fenix V24 WiFi integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import FenixAPI
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    try:
        session = aiohttp.ClientSession()
        try:
            api = FenixAPI(data[CONF_EMAIL], data[CONF_PASSWORD], session)
            if not await api.login():
                raise InvalidAuth
            user_data = await api.get_user()
            if not user_data or not user_data.get("smarthomes"):
                raise CannotConnect
            return {"title": data[CONF_EMAIL]}
        finally:
            await session.close()
    except aiohttp.ClientError as err:
        _LOGGER.error("Connection error: %s", err)
        raise CannotConnect from err


class FenixV24ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fenix V24 WiFi."""

    VERSION = 1
    REAUTH_SCHEMA = STEP_USER_DATA_SCHEMA

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth."""
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                return self.async_abort(reason="invalid_auth")
            except CannotConnect:
                return self.async_abort(reason="cannot_connect")

            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(step_id="reauth", data_schema=STEP_USER_DATA_SCHEMA)


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
