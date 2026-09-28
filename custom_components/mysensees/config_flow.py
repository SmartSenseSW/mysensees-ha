from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiError, AuthError, MySenseesApiClient
from .const import CONF_BASE_URL, CONF_GATEWAY_ID, DEFAULT_BASE_URL, DOMAIN


class MySenseesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MySensees."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_GATEWAY_ID])
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = MySenseesApiClient(
                session=session,
                base_url=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )

            try:
                await client.async_login()
                gateway = await client.async_get_gateway(user_input[CONF_GATEWAY_ID])
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                title = (
                    gateway.get("editable", {}).get("name")
                    or user_input[CONF_GATEWAY_ID]
                )
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_GATEWAY_ID): str,
                }
            ),
            errors=errors,
        )
