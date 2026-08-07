"""aiohttp session for Magewell mwapi.

Magewell login sets a session cookie (e.g. sid=…). aiohttp's default CookieJar
rejects cookies for bare IP hosts (e.g. http://192.168.1.10/); hostnames do not
have that restriction. CookieJar(unsafe=True) keeps sessions for IP or hostname.
"""

from __future__ import annotations

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession


def async_create_magewell_session(
    hass: HomeAssistant, *, verify_ssl: bool
) -> aiohttp.ClientSession:
    """ClientSession that persists mwapi session cookies for IP or hostname."""
    return async_create_clientsession(
        hass,
        verify_ssl=verify_ssl,
        cookie_jar=aiohttp.CookieJar(unsafe=True),
    )
