"""Config flow for 北京用电信息查询 integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector
from requests import RequestException

from .const import DOMAIN, LOGGER
from .sgcc import SGCCData, InvalidData

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("openid"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.
    """
    session = async_get_clientsession(hass)
    openid = data["openid"]
    api: SGCCData
    if openid:
        api = SGCCData(session, openid)
        try:
            await api.async_get_token()
            cons_nos = await api.async_get_cons_nos()
            return {"cons_nos": cons_nos, "openid": data["openid"]}
        except InvalidData as exc:
            LOGGER.error(exc)
            raise InvalidAuth
        except RequestException:
            raise CannotConnect
    else:
        raise InvalidFormat


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 北京用电信息查询."""

    VERSION = 1
    data = None

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.data = info
                return await self.async_step_account(user_input=None)
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_account(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data["consNo"] = user_input["consNo"]
            return self.async_create_entry(title="用户号：" + user_input["consNo"], data=self.data)

        options = []
        for cons_no, cons_name in self.data["cons_nos"].items():
            options.append({"value": cons_no, "label": f'{cons_name}({cons_no})'})

        data_schema = {vol.Required("consNo"): str, "consNo": selector({
            "select": {
                "options": options,
            }
        })}
        return self.async_show_form(
            step_id="account", data_schema=vol.Schema(data_schema), errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidFormat(HomeAssistantError):
    """Error to indicate there is invalid format."""
