"""Resolve integration coordinator from service call data."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import MagewellDecoderCoordinator


def coordinator_from_service(
    hass: HomeAssistant, call: ServiceCall
) -> MagewellDecoderCoordinator:
    """Return coordinator for config_entry_id or Source select entity_id."""
    entry_id = call.data.get("config_entry_id")
    entity_id = call.data.get("entity_id")

    if entity_id:
        registry = er.async_get(hass)
        entity = registry.async_get(entity_id)
        if entity is None or entity.platform != DOMAIN:
            raise HomeAssistantError(
                f"Entity {entity_id} is not from {DOMAIN}"
            )
        entry_id = entity.config_entry_id

    if not entry_id:
        raise HomeAssistantError(
            "Provide config_entry_id or entity_id (Source select entity)"
        )

    coordinator: MagewellDecoderCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry_id
    )
    if coordinator is None:
        raise HomeAssistantError(
            f"Magewell Decoder config entry is not loaded: {entry_id}"
        )
    return coordinator
