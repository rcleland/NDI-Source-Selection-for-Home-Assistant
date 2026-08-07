"""Config flow for Magewell Pro Convert Decoder."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.util.network import is_host_valid
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .host_util import connection_unique_id, normalize_host
from .mwapi import (
    AuthRequired,
    AuthSessionFailed,
    CannotConnect,
    InvalidAuth,
    async_validate_connection,
)

_CONNECTION_DEFAULTS: dict[str, Any] = {
    CONF_USE_SSL: False,
    CONF_VERIFY_SSL: True,
    "port": "",
}

_FLOW_ERRORS = {
    CannotConnect: "cannot_connect",
    AuthRequired: "auth_required",
    InvalidAuth: "invalid_auth",
    AuthSessionFailed: "auth_session_failed",
}


def _password_text_selector() -> TextSelector:
    try:
        from homeassistant.helpers.selector import TextSelectorConfig, TextSelectorType

        return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
    except (ImportError, AttributeError, TypeError):
        return TextSelector()


def _parse_port_value(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    port = int(str(raw).strip())
    if not 1 <= port <= 65535:
        raise ValueError("invalid port")
    return port


def _resolve_port(user_input: dict[str, Any]) -> int:
    use_ssl = bool(user_input[CONF_USE_SSL])
    port = _parse_port_value(user_input.get("port"))
    if port is None:
        return DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP
    return port


def _connection_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("host"): TextSelector(),
            vol.Optional("port"): TextSelector(),
            vol.Required(CONF_USE_SSL): BooleanSelector(),
            vol.Required(CONF_VERIFY_SSL): BooleanSelector(),
            vol.Optional(CONF_USERNAME): TextSelector(),
            vol.Optional(CONF_PASSWORD): _password_text_selector(),
        }
    )


def _prepare_connection_input(user_input: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(user_input)
    prepared["host"] = normalize_host(prepared["host"])
    prepared["port"] = _resolve_port(prepared)
    return prepared


def _connection_suggested(user_input: dict[str, Any] | None) -> dict[str, Any]:
    suggested = dict(_CONNECTION_DEFAULTS)
    if user_input:
        suggested.update(user_input)
    return suggested


def _validate_host_port(
    user_input: dict[str, Any], errors: dict[str, str]
) -> dict[str, Any] | None:
    host = normalize_host(user_input["host"])
    if not is_host_valid(host):
        errors["host"] = "invalid_host"
        return None
    try:
        _parse_port_value(user_input.get("port"))
    except ValueError:
        errors["port"] = "invalid_port"
        return None
    return _prepare_connection_input(user_input)


async def _validate_or_error(
    hass: HomeAssistant, prepared: dict[str, Any], errors: dict[str, str]
) -> bool:
    try:
        await async_validate_connection(hass, prepared)
    except (CannotConnect, AuthRequired, InvalidAuth, AuthSessionFailed) as err:
        errors["base"] = _FLOW_ERRORS[type(err)]
        return False
    return True


def _entry_credentials(prepared: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if u := (prepared.get(CONF_USERNAME) or "").strip():
        data[CONF_USERNAME] = u
    if prepared.get(CONF_PASSWORD):
        data[CONF_PASSWORD] = prepared[CONF_PASSWORD]
    return data


class MagewellDecoderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return MagewellDecoderOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            prepared = _validate_host_port(user_input, errors)
            if prepared and await _validate_or_error(self.hass, prepared, errors):
                host = prepared["host"]
                use_ssl = prepared[CONF_USE_SSL]
                await self.async_set_unique_id(
                    connection_unique_id(host, prepared["port"], use_ssl)
                )
                self._abort_if_unique_id_configured()
                data = {
                    "host": host,
                    "port": prepared["port"],
                    CONF_USE_SSL: use_ssl,
                    CONF_VERIFY_SSL: prepared[CONF_VERIFY_SSL],
                    **_entry_credentials(prepared),
                }
                return self.async_create_entry(
                    title=f"Magewell Decoder ({host})",
                    data=data,
                    options={"scan_interval": DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(), _connection_suggested(user_input)
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            prepared = _validate_host_port(user_input, errors)
            if prepared and await _validate_or_error(self.hass, prepared, errors):
                host = prepared["host"]
                new_data = {
                    "host": host,
                    "port": prepared["port"],
                    CONF_USE_SSL: prepared[CONF_USE_SSL],
                    CONF_VERIFY_SSL: prepared[CONF_VERIFY_SSL],
                    **_entry_credentials(prepared),
                }
                if CONF_USERNAME not in new_data and CONF_USERNAME in entry.data:
                    new_data[CONF_USERNAME] = entry.data[CONF_USERNAME]
                if CONF_PASSWORD not in new_data and CONF_PASSWORD in entry.data:
                    new_data[CONF_PASSWORD] = entry.data[CONF_PASSWORD]
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=new_data,
                    unique_id=connection_unique_id(
                        host, prepared["port"], prepared[CONF_USE_SSL]
                    ),
                )
                return self.async_abort(reason="reconfigure_successful")

        suggested = _connection_suggested(user_input)
        port = entry.data.get("port")
        suggested.update(
            {
                "host": entry.data["host"],
                "port": "" if port in (None, "") else str(port),
                CONF_USE_SSL: entry.data[CONF_USE_SSL],
                CONF_VERIFY_SSL: entry.data.get(CONF_VERIFY_SSL, True),
                CONF_USERNAME: entry.data.get(CONF_USERNAME, ""),
                CONF_PASSWORD: "",
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(), suggested
            ),
            errors=errors,
        )


class MagewellDecoderOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = int(
            self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        )
        schema = vol.Schema(
            {
                vol.Required("scan_interval"): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.SLIDER,
                        min=10,
                        max=600,
                        step=5,
                        unit_of_measurement="s",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, {"scan_interval": current}
            ),
        )
