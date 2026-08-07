"""Magewell Pro Convert Decoder integration (HTTP API)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import DOMAIN
from .coordinator import MagewellDecoderCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
]

_TARGET_FIELDS = {
    vol.Optional("config_entry_id"): cv.string,
    vol.Optional("entity_id"): cv.entity_id,
}

SET_NDI_STREAM_SCHEMA = vol.All(
    vol.Schema(
        {
            **_TARGET_FIELDS,
            vol.Required("ndi_name"): cv.string,
            vol.Optional("ndi_ip_port"): cv.string,
            vol.Optional("preset_label", default="HA NDI"): cv.string,
            vol.Optional("buffer_duration", default=60): vol.Coerce(int),
        }
    ),
    cv.has_at_least_one_key("config_entry_id", "entity_id"),
)

SET_HTTP_STREAM_SCHEMA = vol.All(
    vol.Schema(
        {
            **_TARGET_FIELDS,
            vol.Required("channel_name"): cv.string,
            vol.Required("url"): cv.string,
            vol.Optional("update_if_exists", default=True): cv.boolean,
        }
    ),
    cv.has_at_least_one_key("config_entry_id", "entity_id"),
)

SWITCH_SOURCE_SCHEMA = vol.All(
    vol.Schema(
        {
            **_TARGET_FIELDS,
            vol.Required("source"): cv.string,
            vol.Optional("source_type", default="auto"): vol.In(
                ("auto", "ndi", "preset")
            ),
        }
    ),
    cv.has_at_least_one_key("config_entry_id", "entity_id"),
)


def _coordinator_from_service(
    hass: HomeAssistant, call: ServiceCall
) -> MagewellDecoderCoordinator:
    """Return coordinator for config_entry_id or Source select entity_id."""
    entry_id = call.data.get("config_entry_id")
    entity_id = call.data.get("entity_id")

    if entity_id:
        entity = er.async_get(hass).async_get(entity_id)
        if entity is None or entity.platform != DOMAIN:
            raise HomeAssistantError(f"Entity {entity_id} is not from {DOMAIN}")
        entry_id = entity.config_entry_id

    if not entry_id:
        raise HomeAssistantError(
            "Provide config_entry_id or entity_id (Source select entity)"
        )

    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None:
        raise HomeAssistantError(
            f"Magewell Decoder config entry is not loaded: {entry_id}"
        )
    return coordinator


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register services once (scripts / scenes / automations)."""

    if hass.services.has_service(DOMAIN, "set_ndi_stream"):
        return True

    async def async_set_ndi_stream(call: ServiceCall) -> None:
        coordinator = _coordinator_from_service(hass, call)
        await coordinator.async_set_ndi_stream_name(
            call.data["ndi_name"],
            ndi_ip_port=call.data.get("ndi_ip_port"),
            preset_label=call.data["preset_label"],
            buffer_duration=int(call.data["buffer_duration"]),
        )

    async def async_set_http_stream(call: ServiceCall) -> None:
        coordinator = _coordinator_from_service(hass, call)
        await coordinator.async_set_http_stream(
            call.data["channel_name"],
            call.data["url"],
            update_if_exists=call.data["update_if_exists"],
        )

    async def async_switch_source(call: ServiceCall) -> None:
        coordinator = _coordinator_from_service(hass, call)
        await coordinator.async_switch_source_by_name(
            call.data["source"],
            source_type=call.data["source_type"],
        )

    hass.services.async_register(
        DOMAIN,
        "set_ndi_stream",
        async_set_ndi_stream,
        schema=SET_NDI_STREAM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "set_http_stream",
        async_set_http_stream,
        schema=SET_HTTP_STREAM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "switch_source",
        async_switch_source,
        schema=SWITCH_SOURCE_SCHEMA,
    )
    _LOGGER.debug("Registered %s services", DOMAIN)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    coordinator = MagewellDecoderCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            coordinator.cancel_pending_refresh()
    return unload_ok
