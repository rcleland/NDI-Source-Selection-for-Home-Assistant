"""Magewell mwapi HTTP client (session, auth, JSON requests)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from .host_util import build_origin_url

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Unable to reach device or invalid response."""


class AuthRequired(Exception):
    """Device requires mwapi login (status 37)."""


class InvalidAuth(Exception):
    """Login rejected (e.g. status 36)."""


class AuthSessionFailed(Exception):
    """Login succeeded but the next mwapi call was still not authenticated."""


def password_md5_hex(plain: str) -> str:
    """API expects pass= MD5 hex digest of the password."""
    return hashlib.md5(plain.encode("utf-8")).hexdigest()


def async_create_magewell_session(
    hass: HomeAssistant, *, verify_ssl: bool
) -> aiohttp.ClientSession:
    """ClientSession that persists mwapi session cookies for IP or hostname."""
    return async_create_clientsession(
        hass,
        verify_ssl=verify_ssl,
        cookie_jar=aiohttp.CookieJar(unsafe=True),
    )


async def async_mwapi_json(
    session: aiohttp.ClientSession,
    base_url: str,
    method: str,
    extra_params: dict[str, str] | None = None,
    *,
    timeout: int = 15,
) -> tuple[int | None, dict[str, Any] | None]:
    """GET mwapi with method=… and optional extra query params."""
    params: dict[str, str] = {"method": method}
    if extra_params:
        params.update({k: str(v) for k, v in extra_params.items()})
    url = f"{base_url}/mwapi"
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with session.get(url, params=params, timeout=client_timeout) as resp:
            text = await resp.text()
    except aiohttp.ClientError as err:
        _LOGGER.debug("mwapi %s failed: %s", method, err)
        return None, None
    if resp.status != 200:
        return resp.status, None
    try:
        return resp.status, json.loads(text)
    except json.JSONDecodeError:
        _LOGGER.debug("mwapi %s returned non-JSON: %s", method, text[:200])
        return resp.status, None


async def async_validate_connection(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Ping and get-channel; login if device returns status 37."""
    base = build_origin_url(data["host"], int(data["port"]), bool(data["use_ssl"]))
    verify_ssl = bool(data.get(CONF_VERIFY_SSL, True))
    session = async_create_magewell_session(hass, verify_ssl=verify_ssl)
    short_timeout = 10

    _status, ping = await async_mwapi_json(
        session, base, "ping", timeout=short_timeout
    )
    if _status != 200 or not isinstance(ping, dict):
        raise CannotConnect

    _status, channel = await async_mwapi_json(
        session, base, "get-channel", timeout=short_timeout
    )
    if _status != 200 or not isinstance(channel, dict):
        raise CannotConnect

    st = channel.get("status")
    if st == 0:
        return
    if st != 37:
        return  # device answered; do not block setup for other statuses

    username = (data.get(CONF_USERNAME) or "").strip()
    password = data.get(CONF_PASSWORD) or ""
    if not username or not password:
        raise AuthRequired

    _status, login = await async_mwapi_json(
        session,
        base,
        "login",
        {"id": username, "pass": password_md5_hex(password)},
        timeout=short_timeout,
    )
    if not isinstance(login, dict):
        raise CannotConnect
    if login.get("status") == 36:
        raise InvalidAuth
    if login.get("status") != 0:
        raise CannotConnect

    _status, channel2 = await async_mwapi_json(
        session, base, "get-channel", timeout=short_timeout
    )
    if not isinstance(channel2, dict) or channel2.get("status") != 0:
        _LOGGER.warning(
            "After login, get-channel still returned status=%s",
            channel2.get("status") if isinstance(channel2, dict) else channel2,
        )
        raise AuthSessionFailed
