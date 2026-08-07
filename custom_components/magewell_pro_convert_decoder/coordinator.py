"""Data update coordinator for Magewell Pro Convert Decoder."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_normalize import (
    NDI_PREFIX,
    PRESET_PREFIX,
    build_ntkndi_url,
    decode_source_option,
    encode_source_option,
    extract_video_info,
    ndi_display_name,
    ndi_source_address,
    normalize_ndi_sources,
    normalize_preset_channels,
    parse_current_channel,
)
from .const import (
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SOURCE_SIGNAL_REFRESH_DELAY,
)
from .host_util import build_origin_url
from .mwapi import async_create_magewell_session, async_mwapi_json, password_md5_hex

_LOGGER = logging.getLogger(__name__)


def _api_status(body: dict[str, Any] | None) -> int | None:
    return body.get("status") if isinstance(body, dict) else None


def _parse_on_ok(
    result: tuple[int | None, dict[str, Any] | None],
    parser: Callable[[dict[str, Any]], Any],
) -> tuple[int | None, Any]:
    """Return API status and parsed data when status == 0."""
    _http, body = result
    status = _api_status(body)
    if status == 0 and isinstance(body, dict):
        return status, parser(body)
    return status, None


class MagewellDecoderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll decoder mwapi: ping, NDI sources, channels, signal info."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.config_entry = entry
        self._base_url = build_origin_url(
            entry.data["host"],
            int(entry.data["port"]),
            entry.data[CONF_USE_SSL],
        )
        verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)
        self._session = async_create_magewell_session(hass, verify_ssl=verify_ssl)
        scan_seconds = int(entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_seconds),
        )
        self._signal_refresh_task: asyncio.Task[None] | None = None

    def cancel_pending_refresh(self) -> None:
        if self._signal_refresh_task and not self._signal_refresh_task.done():
            self._signal_refresh_task.cancel()
        self._signal_refresh_task = None

    async def _on_source_changed(self) -> None:
        """Refresh now (source name) and again after signal lock delay (aspect/fps)."""
        await self.async_request_refresh()
        self.cancel_pending_refresh()

        async def _delayed_signal_refresh() -> None:
            try:
                await asyncio.sleep(SOURCE_SIGNAL_REFRESH_DELAY)
                await self.async_request_refresh()
            except asyncio.CancelledError:
                pass

        self._signal_refresh_task = asyncio.create_task(_delayed_signal_refresh())

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer="Magewell",
            model="Pro Convert Decoder",
            configuration_url=self._base_url,
        )

    async def _mwapi(
        self, method: str, extra_params: dict[str, str] | None = None
    ) -> tuple[int | None, dict[str, Any] | None]:
        return await async_mwapi_json(self._session, self._base_url, method, extra_params)

    async def async_select_source(self, option: str) -> None:
        try:
            is_ndi, name = decode_source_option(option)
        except ValueError as err:
            raise HomeAssistantError("Invalid source selection") from err
        await self._set_channel(name=name, is_ndi=is_ndi)

    async def async_switch_source_by_name(
        self, source: str, *, source_type: str = "auto"
    ) -> None:
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

        if self.data:
            preset_names = {
                ch.get("name", "").strip()
                for ch in self.data.get("preset_channels") or []
                if isinstance(ch.get("name"), str) and ch.get("name", "").strip()
            }
            for row in self.data.get("ndi_sources") or []:
                if isinstance(row, dict) and ndi_display_name(row) == source:
                    await self.async_set_ndi_stream_name(source)
                    return
            if source in preset_names:
                await self._set_channel(name=source, is_ndi=False)
                return

        _st, probe = await self._mwapi(
            "set-channel", {"ndi-name": "true", "name": source}
        )
        if probe is not None and probe.get("status") == 0:
            await self._on_source_changed()
            return
        await self._set_channel(name=source, is_ndi=False)

    async def _set_channel(self, name: str, *, is_ndi: bool) -> None:
        _status, data = await self._mwapi(
            "set-channel",
            {"ndi-name": "true" if is_ndi else "false", "name": name},
        )
        if data is None:
            raise HomeAssistantError("Device did not respond to set-channel")
        if data.get("status") != 0:
            raise HomeAssistantError(
                f"set-channel rejected (status {data.get('status')!r})"
            )
        await self._on_source_changed()

    async def async_set_ndi_stream_name(
        self,
        ndi_name: str,
        *,
        ndi_ip_port: str | None = None,
        preset_label: str = "HA NDI",
        buffer_duration: int = 60,
    ) -> None:
        ndi_name = ndi_name.strip()
        if not ndi_name:
            raise HomeAssistantError("ndi_name is required")

        _st, probe = await self._mwapi(
            "set-channel", {"ndi-name": "true", "name": ndi_name}
        )
        if probe is not None and probe.get("status") == 0:
            await self._on_source_changed()
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
                "Pass ndi_ip_port or wait until get-ndi-sources lists this stream."
            )

        label = preset_label.strip() or "HA NDI"
        await self._add_or_update_preset(label, build_ntkndi_url(ndi_name, ip, buffer_duration))
        await self._set_channel(name=label, is_ndi=False)

    async def async_set_http_stream(
        self,
        channel_name: str,
        url: str,
        *,
        update_if_exists: bool = True,
    ) -> None:
        channel_name = channel_name.strip()
        url = url.strip()
        if not channel_name or not url:
            raise HomeAssistantError("channel_name and url are required")
        await self._add_or_update_preset(channel_name, url, update_if_exists=update_if_exists)
        await self._set_channel(name=channel_name, is_ndi=False)

    async def _add_or_update_preset(
        self, name: str, url: str, *, update_if_exists: bool = True
    ) -> None:
        _lst_st, lst = await self._mwapi("list-channels")
        names: set[str] = set()
        if lst and lst.get("status") == 0:
            names = {
                ch["name"]
                for ch in normalize_preset_channels(lst)
                if isinstance(ch.get("name"), str)
            }

        if name in names and update_if_exists:
            _st, data = await self._mwapi(
                "modify-channel", {"name": name, "new-name": name, "url": url}
            )
        else:
            _st, data = await self._mwapi("add-channel", {"name": name, "url": url})
            if (
                data is not None
                and data.get("status") != 0
                and update_if_exists
            ):
                _st, data = await self._mwapi(
                    "modify-channel", {"name": name, "new-name": name, "url": url}
                )

        if data is None:
            raise HomeAssistantError("add-channel/modify-channel: no JSON response")
        if data.get("status") != 0:
            raise HomeAssistantError(
                f"Channel update rejected (status {data.get('status')!r})"
            )

    async def _async_ensure_logged_in(self) -> None:
        username = (self.config_entry.data.get(CONF_USERNAME) or "").strip()
        password = self.config_entry.data.get(CONF_PASSWORD) or ""
        if not username or not password:
            return
        _s, data = await self._mwapi(
            "login", {"id": username, "pass": password_md5_hex(password)}
        )
        if data is None or data.get("status") != 0:
            _LOGGER.warning(
                "Magewell mwapi login failed for %s (status=%s)",
                username,
                data.get("status") if isinstance(data, dict) else None,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        await self._async_ensure_logged_in()

        ping_r, ndi_r, list_r, channel_r, signal_r = await asyncio.gather(
            self._mwapi("ping"),
            self._mwapi("get-ndi-sources"),
            self._mwapi("list-channels"),
            self._mwapi("get-channel"),
            self._mwapi("get-signal-info"),
        )

        ping_status, ping_data = ping_r
        reachable = ping_status == 200 and _api_status(ping_data) == 0

        ndi_status, ndi_sources = _parse_on_ok(ndi_r, normalize_ndi_sources)
        list_status, preset_channels = _parse_on_ok(list_r, normalize_preset_channels)

        channel_status = _api_status(channel_r[1])
        ch_body = channel_r[1]
        if channel_status == 37:
            current_source = None
        elif isinstance(ch_body, dict):
            current_source = parse_current_channel(ch_body)
        else:
            current_source = None

        signal_status, video_info = _parse_on_ok(signal_r, extract_video_info)

        select_options: list[str] = []
        for src in ndi_sources or []:
            if label := ndi_display_name(src):
                select_options.append(encode_source_option(True, label))
        for ch in preset_channels or []:
            if isinstance(ch.get("name"), str) and (n := ch["name"].strip()):
                select_options.append(encode_source_option(False, n))

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

        return {
            "reachable": reachable,
            "http_status": ping_status,
            "api_status": _api_status(ping_data),
            "error": None if reachable else "ping_failed",
            "ndi_sources": ndi_sources or [],
            "preset_channels": preset_channels or [],
            "current_source": current_source,
            "video_info": video_info,
            "select_options": select_options,
            "current_select_option": current_select_option,
            "api_status_get_channel": channel_status,
            "api_status_get_ndi_sources": ndi_status,
            "api_status_list_channels": list_status,
            "api_status_get_signal_info": signal_status,
            "auth_configured": auth_configured,
            "auth_required_by_device": (
                channel_status == 37 and not auth_configured and reachable
            ),
        }
