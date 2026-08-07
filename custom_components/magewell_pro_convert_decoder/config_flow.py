"""Config flow for Magewell Pro Convert Decoder."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
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

from .auth import password_md5_hex
from .host_util import build_origin_url, connection_unique_id, normalize_host
from .http_session import async_create_magewell_session
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

_LOGGER = logging.getLogger(__name__)

_CONNECTION_DEFAULTS: dict[str, Any] = {
    CONF_USE_SSL: False,
    CONF_VERIFY_SSL: True,
    "port": "",
}


def _password_text_selector() -> TextSelector:
    """Mask password in UI when supported; plain TextSelector otherwise."""
    try:
        from homeassistant.helpers.selector import TextSelectorConfig, TextSelectorType

        return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
    except (ImportError, AttributeError, TypeError):
        return TextSelector()


def _parse_port_value(raw: Any) -> int | None:
    """Return port int, None if blank, raise ValueError if invalid."""
    if raw in (None, ""):
        return None
    port = int(str(raw).strip())
    if not 1 <= port <= 65535:
        raise ValueError("invalid port")
    return port


def _resolve_port(user_input: dict[str, Any]) -> int:
    """Default empty port to 80/443 based on SSL."""
    use_ssl = bool(user_input[CONF_USE_SSL])
    port = _parse_port_value(user_input.get("port"))
    if port is None:
        return DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP
    return port


class CannotConnect(Exception):
    """Unable to reach device or invalid response."""


class AuthRequired(Exception):
    """Device requires mwapi login (status 37)."""


class InvalidAuth(Exception):
    """Login rejected (e.g. status 36)."""


class AuthSessionFailed(Exception):
    """Login reported success but the next mwapi call was still not authenticated."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Ping, then ensure get-channel works (login if device returns 37)."""
    base = build_origin_url(data["host"], int(data["port"]), bool(data[CONF_USE_SSL]))
    verify_ssl = bool(data.get(CONF_VERIFY_SSL, True))
    session = async_create_magewell_session(hass, verify_ssl=verify_ssl)
    url = f"{base}/mwapi"
    to = aiohttp.ClientTimeout(total=10)

    try:
        async with session.get(url, params={"method": "ping"}, timeout=to) as resp:
            text = await resp.text()
    except aiohttp.ClientError as err:
        _LOGGER.debug("Validation ping failed: %s", err)
        raise CannotConnect from err

    if resp.status != 200:
        raise CannotConnect
    try:
        json.loads(text)
    except json.JSONDecodeError as err:
        raise CannotConnect from err

    try:
        async with session.get(url, params={"method": "get-channel"}, timeout=to) as resp:
            ch_text = await resp.text()
    except aiohttp.ClientError as err:
        raise CannotConnect from err

    if resp.status != 200:
        raise CannotConnect
    try:
        ch = json.loads(ch_text)
    except json.JSONDecodeError as err:
        raise CannotConnect from err

    st = ch.get("status") if isinstance(ch, dict) else None
    if st == 0:
        return
    if st == 37:
        username = (data.get(CONF_USERNAME) or "").strip()
        password = data.get(CONF_PASSWORD) or ""
        if not username or not password:
            raise AuthRequired
        try:
            async with session.get(
                url,
                params={
                    "method": "login",
                    "id": username,
                    "pass": password_md5_hex(password),
                },
                timeout=to,
            ) as resp_login:
                login_text = await resp_login.text()
        except aiohttp.ClientError as err:
            raise CannotConnect from err
        try:
            login_body = json.loads(login_text)
        except json.JSONDecodeError as err:
            raise CannotConnect from err
        lst = login_body.get("status") if isinstance(login_body, dict) else None
        if lst != 0:
            if lst == 36:
                raise InvalidAuth
            raise CannotConnect
        async with session.get(url, params={"method": "get-channel"}, timeout=to) as resp2:
            ch2_text = await resp2.text()
        try:
            ch2 = json.loads(ch2_text)
        except json.JSONDecodeError as err:
            raise CannotConnect from err
        if not isinstance(ch2, dict) or ch2.get("status") != 0:
            _LOGGER.warning(
                "After login success, get-channel still returned status=%s "
                "(session cookie may not have been stored)",
                ch2.get("status") if isinstance(ch2, dict) else ch2,
            )
            raise AuthSessionFailed
        return
    # Other statuses: device answered; do not block adding the integration.


def _connection_schema() -> vol.Schema:
    """Frontend-serializable schema (selectors only, no vol.Coerce/vol.Any)."""
    return vol.Schema(
        {
            vol.Required("host"): TextSelector(),
            # TextSelector allows blank; port is parsed in async_step_*.
            vol.Optional("port"): TextSelector(),
            vol.Required(CONF_USE_SSL): BooleanSelector(),
            vol.Required(CONF_VERIFY_SSL): BooleanSelector(),
            vol.Optional(CONF_USERNAME): TextSelector(),
            vol.Optional(CONF_PASSWORD): _password_text_selector(),
        }
    )


def _prepare_connection_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize host/port for validation and storage."""
    prepared = dict(user_input)
    prepared["host"] = normalize_host(prepared["host"])
    prepared["port"] = _resolve_port(prepared)
    return prepared


def _connection_suggested(user_input: dict[str, Any] | None) -> dict[str, Any]:
    """Merge user input with form defaults for add_suggested_values_to_schema()."""
    suggested = dict(_CONNECTION_DEFAULTS)
    if user_input:
        suggested.update(user_input)
    return suggested


class MagewellDecoderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a UI config flow."""

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
            host = normalize_host(user_input["host"])
            if not is_host_valid(host):
                errors["host"] = "invalid_host"
            else:
                try:
                    _parse_port_value(user_input.get("port"))
                except ValueError:
                    errors["port"] = "invalid_port"
                else:
                    prepared = _prepare_connection_input(user_input)
                    use_ssl = prepared[CONF_USE_SSL]
                    try:
                        await validate_input(self.hass, prepared)
                    except CannotConnect:
                        errors["base"] = "cannot_connect"
                    except AuthRequired:
                        errors["base"] = "auth_required"
                    except InvalidAuth:
                        errors["base"] = "invalid_auth"
                    except AuthSessionFailed:
                        errors["base"] = "auth_session_failed"
                    else:
                        await self.async_set_unique_id(
                            connection_unique_id(host, prepared["port"], use_ssl)
                        )
                        self._abort_if_unique_id_configured()
                        data: dict[str, Any] = {
                            "host": host,
                            "port": prepared["port"],
                            CONF_USE_SSL: use_ssl,
                            CONF_VERIFY_SSL: prepared[CONF_VERIFY_SSL],
                        }
                        u = (prepared.get(CONF_USERNAME) or "").strip()
                        if u:
                            data[CONF_USERNAME] = u
                        if prepared.get(CONF_PASSWORD):
                            data[CONF_PASSWORD] = prepared[CONF_PASSWORD]
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
        """Update host, SSL, or API credentials."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = normalize_host(user_input["host"])
            if not is_host_valid(host):
                errors["host"] = "invalid_host"
            else:
                try:
                    _parse_port_value(user_input.get("port"))
                except ValueError:
                    errors["port"] = "invalid_port"
                else:
                    prepared = _prepare_connection_input(user_input)
                    new_data: dict[str, Any] = {
                        "host": host,
                        "port": prepared["port"],
                        CONF_USE_SSL: prepared[CONF_USE_SSL],
                        CONF_VERIFY_SSL: prepared[CONF_VERIFY_SSL],
                    }
                    u = (prepared.get(CONF_USERNAME) or "").strip()
                    if u:
                        new_data[CONF_USERNAME] = u
                    elif CONF_USERNAME in entry.data:
                        new_data[CONF_USERNAME] = entry.data[CONF_USERNAME]
                    if prepared.get(CONF_PASSWORD):
                        new_data[CONF_PASSWORD] = prepared[CONF_PASSWORD]
                    elif CONF_PASSWORD in entry.data:
                        new_data[CONF_PASSWORD] = entry.data[CONF_PASSWORD]
                    try:
                        await validate_input(self.hass, new_data)
                    except CannotConnect:
                        errors["base"] = "cannot_connect"
                    except AuthRequired:
                        errors["base"] = "auth_required"
                    except InvalidAuth:
                        errors["base"] = "invalid_auth"
                    except AuthSessionFailed:
                        errors["base"] = "auth_session_failed"
                    else:
                        self.hass.config_entries.async_update_entry(
                            entry,
                            data=new_data,
                            unique_id=connection_unique_id(
                                host,
                                prepared["port"],
                                prepared[CONF_USE_SSL],
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
    """Poll interval options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        current = int(entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL))
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
