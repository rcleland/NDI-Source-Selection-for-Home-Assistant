"""Data update coordinator for Magewell Pro Convert Decoder."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any
from urllib.parse import quote

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_normalize import (
    extract_video_info,
    ndi_display_name,
    ndi_source_address,
    normalize_ndi_sources,
    normalize_preset_channels,
    parse_current_channel,
)
from .auth import password_md5_hex
from .host_util import build_origin_url
from .http_session import async_create_magewell_session
from .const import (
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .source_encoding import (
    NDI_PREFIX,
    PRESET_PREFIX,
    decode_source_option,
    encode_source_option,
)

_LOGGER = logging.getLogger(__name__)


def build_base_url(entry: ConfigEntry) -> str:
    """Build origin URL (scheme + host + port) from config entry."""
    return build_origin_url(
        entry.data["host"],
        int(entry.data["port"]),
        entry.data[CONF_USE_SSL],
    )


def build_ntkndi_url(ndi_stream_name: str, ip_port: str, buffer_ms: int) -> str:
    """Preset URL for NDI via add-channel (Magewell ntkndi scheme)."""
    qn = quote(ndi_stream_name, safe="")
    qu = quote(ip_port, safe="")
    return f"ntkndi://ndi?name={qn}&url={qu}&mw-buffer-duration={buffer_ms}"


class MagewellDecoderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll decoder mwapi: ping, NDI sources, channels, signal info."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.config_entry = entry
        self._base_url = build_base_url(entry)
        verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)
        self._session = async_create_magewell_session(hass, verify_ssl=verify_ssl)
        scan_seconds = int(entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_seconds),
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Shared device info for all entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer="Magewell",
            model="Pro Convert Decoder",
            configuration_url=self._base_url,
        )

    async def _mwapi_json(
        self, method: str, extra_params: dict[str, str] | None = None
    ) -> tuple[int | None, dict[str, Any] | None]:
        """GET mwapi with method=… and optional extra query params."""
        params: dict[str, str] = {"method": method}
        if extra_params:
            for k, v in extra_params.items():
                params[k] = v if isinstance(v, str) else str(v)
        try:
            async with self._session.get(
                f"{self._base_url}/mwapi",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
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

    async def async_select_source(self, option: str) -> None:
        """Apply set-channel for a select option string."""
        try:
            is_ndi, name = decode_source_option(option)
        except ValueError as err:
            raise HomeAssistantError("Invalid source selection") from err

        await self._set_channel(name=name, is_ndi=is_ndi)

    async def async_switch_source_by_name(
        self, source: str, *, source_type: str = "auto"
    ) -> None:
        """Switch to a preset or NDI source using a plain name (for buttons/automations).

        source_type: auto (default), ndi, or preset.
        """
        source = source.strip()
        if not source:
            raise HomeAssistantError("source is required")

        if source.startswith(NDI_PREFIX) or source.startswith(PRESET_PREFIX):
            await self.async_select_source(source)
            return

        source_type = source_type.strip().lower()
        if source_type not in ("auto", "ndi", "preset"):
            raise HomeAssistantError("source_type must be auto, ndi, or preset")

        if source_type == "preset":
            await self._set_channel(name=source, is_ndi=False)
            return
        if source_type == "ndi":
            await self.async_set_ndi_stream_name(source)
            return

        preset_names: set[str] = set()
        if self.data:
            for ch in self.data.get("preset_channels") or []:
                n = ch.get("name")
                if isinstance(n, str) and n.strip():
                    preset_names.add(n.strip())
            for row in self.data.get("ndi_sources") or []:
                if isinstance(row, dict) and ndi_display_name(row) == source:
                    await self.async_set_ndi_stream_name(source)
                    return

        if source in preset_names:
            await self._set_channel(name=source, is_ndi=False)
            return

        _st, ndi_probe = await self._mwapi_json(
            "set-channel",
            {"ndi-name": "true", "name": source},
        )
        if ndi_probe is not None and ndi_probe.get("status") == 0:
            await self.async_request_refresh()
            return

        await self._set_channel(name=source, is_ndi=False)

    async def _set_channel(self, name: str, *, is_ndi: bool) -> None:
        _status, data = await self._mwapi_json(
            "set-channel",
            {"ndi-name": "true" if is_ndi else "false", "name": name},
        )
        if data is None:
            raise HomeAssistantError("Device did not respond to set-channel")
        if data.get("status") != 0:
            raise HomeAssistantError(
                f"set-channel rejected (status {data.get('status')!r})"
            )
        await self.async_request_refresh()

    async def async_set_ndi_stream_name(
        self,
        ndi_name: str,
        *,
        ndi_ip_port: str | None = None,
        preset_label: str = "HA NDI",
        buffer_duration: int = 60,
    ) -> None:
        """Select an NDI source by exact stream name; fall back to ntkndi preset + add-channel."""
        ndi_name = ndi_name.strip()
        if not ndi_name:
            raise HomeAssistantError("ndi_name is required")

        _st, probe = await self._mwapi_json(
            "set-channel",
            {"ndi-name": "true", "name": ndi_name},
        )
        if probe is not None and probe.get("status") == 0:
            await self.async_request_refresh()
            return

        ip = (ndi_ip_port or "").strip()
        if not ip and self.data:
            for row in self.data.get("ndi_sources") or []:
                if isinstance(row, dict) and ndi_display_name(row) == ndi_name:
                    ip = ndi_source_address(row) or ""
                    break

        if not ip:
            raise HomeAssistantError(
                "set-channel for this NDI name was rejected and no IP:port was found. "
                "Pass ndi_ip_port (host:port from discovery, e.g. 192.168.1.10:5961) or "
                "wait until get-ndi-sources lists this stream."
            )

        url = build_ntkndi_url(ndi_name, ip, buffer_duration)
        await self._add_or_update_preset(preset_label.strip() or "HA NDI", url)
        await self._set_channel(name=preset_label.strip() or "HA NDI", is_ndi=False)

    async def async_set_http_stream(
        self,
        channel_name: str,
        url: str,
        *,
        update_if_exists: bool = True,
    ) -> None:
        """Add or update an HTTP (or other) preset URL and select it."""
        channel_name = channel_name.strip()
        url = url.strip()
        if not channel_name or not url:
            raise HomeAssistantError("channel_name and url are required")
        await self._add_or_update_preset(channel_name, url, update_if_exists=update_if_exists)
        await self._set_channel(name=channel_name, is_ndi=False)

    async def _add_or_update_preset(
        self, name: str, url: str, *, update_if_exists: bool = True
    ) -> None:
        _lst_st, lst = await self._mwapi_json("list-channels")
        names: set[str] = set()
        if lst and lst.get("status") == 0:
            for ch in normalize_preset_channels(lst):
                n = ch.get("name")
                if isinstance(n, str):
                    names.add(n)

        if name in names and update_if_exists:
            _st, data = await self._mwapi_json(
                "modify-channel",
                {"name": name, "new-name": name, "url": url},
            )
        else:
            _st, data = await self._mwapi_json(
                "add-channel",
                {"name": name, "url": url},
            )
            if (
                data is not None
                and data.get("status") != 0
                and update_if_exists
            ):
                _st, data = await self._mwapi_json(
                    "modify-channel",
                    {"name": name, "new-name": name, "url": url},
                )

        if data is None:
            raise HomeAssistantError("add-channel/modify-channel: no JSON response")
        if data.get("status") != 0:
            raise HomeAssistantError(
                f"Channel update rejected (status {data.get('status')!r})"
            )

    async def _async_ensure_logged_in(self) -> None:
        """Login so session cookie is set for protected mwapi calls (status 37 if skipped)."""
        username = (self.config_entry.data.get(CONF_USERNAME) or "").strip()
        password = self.config_entry.data.get(CONF_PASSWORD) or ""
        if not username or not password:
            return
        _s, data = await self._mwapi_json(
            "login",
            {"id": username, "pass": password_md5_hex(password)},
        )
        if data is None or data.get("status") != 0:
            _LOGGER.warning(
                "Magewell mwapi login failed for %s (status=%s)",
                username,
                data.get("status") if isinstance(data, dict) else None,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        await self._async_ensure_logged_in()

        ping_task = self._mwapi_json("ping")
        ndi_task = self._mwapi_json("get-ndi-sources")
        list_task = self._mwapi_json("list-channels")
        channel_task = self._mwapi_json("get-channel")
        signal_task = self._mwapi_json("get-signal-info")

        (
            ping_result,
            ndi_result,
            list_result,
            channel_result,
            signal_result,
        ) = await asyncio.gather(
            ping_task, ndi_task, list_task, channel_task, signal_task
        )

        ping_status, ping_data = ping_result
        reachable = ping_status == 200 and (
            isinstance(ping_data, dict) and ping_data.get("status") == 0
        )

        ndi_sources: list[dict[str, Any]] = []
        ndi_api_status: int | None = None
        if isinstance(ndi_result[1], dict):
            ndi_api_status = ndi_result[1].get("status")
            if ndi_result[1].get("status") == 0:
                ndi_sources = normalize_ndi_sources(ndi_result[1])

        preset_channels: list[dict[str, Any]] = []
        list_api_status: int | None = None
        if isinstance(list_result[1], dict):
            list_api_status = list_result[1].get("status")
            if list_result[1].get("status") == 0:
                preset_channels = normalize_preset_channels(list_result[1])

        current_source: dict[str, Any] | None = None
        channel_api_status: int | None = None
        ch_body = channel_result[1]
        if isinstance(ch_body, dict):
            channel_api_status = ch_body.get("status")
            if ch_body.get("status") == 37:
                current_source = None
            else:
                current_source = parse_current_channel(ch_body)

        video_info: dict[str, Any] | None = None
        signal_api_status: int | None = None
        if isinstance(signal_result[1], dict):
            signal_api_status = signal_result[1].get("status")
            if signal_result[1].get("status") == 0:
                video_info = extract_video_info(signal_result[1])

        select_options: list[str] = []
        for src in ndi_sources:
            label = ndi_display_name(src)
            if label:
                select_options.append(encode_source_option(True, label))
        for ch in preset_channels:
            n = ch.get("name")
            if isinstance(n, str) and n.strip():
                select_options.append(encode_source_option(False, n.strip()))

        current_select_option: str | None = None
        if current_source:
            current_select_option = encode_source_option(
                current_source["ndi_name"], current_source["name"]
            )
            if current_select_option not in select_options:
                select_options.insert(0, current_select_option)

        auth_configured = bool(
            (self.config_entry.data.get(CONF_USERNAME) or "").strip()
            and self.config_entry.data.get(CONF_PASSWORD)
        )
        auth_required = (
            channel_api_status == 37
            and not auth_configured
            and reachable
        )

        return {
            "reachable": reachable,
            "http_status": ping_status,
            "api_status": (
                ping_data.get("status") if isinstance(ping_data, dict) else None
            ),
            "error": None if reachable else "ping_failed",
            "raw_ping": ping_data,
            "ndi_sources": ndi_sources,
            "preset_channels": preset_channels,
            "current_source": current_source,
            "video_info": video_info,
            "select_options": select_options,
            "current_select_option": current_select_option,
            "api_status_get_channel": channel_api_status,
            "api_status_get_ndi_sources": ndi_api_status,
            "api_status_list_channels": list_api_status,
            "api_status_get_signal_info": signal_api_status,
            "auth_configured": auth_configured,
            "auth_required_by_device": auth_required,
        }
