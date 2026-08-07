"""Binary sensors for Magewell Pro Convert Decoder."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import DOMAIN
from .coordinator import MagewellDecoderCoordinator
from .entity import MagewellEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: MagewellDecoderCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MagewellDecoderReachableEntity(coordinator)])


class MagewellDecoderReachableEntity(MagewellEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "decoder_reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: MagewellDecoderCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_reachable"

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("reachable"))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data:
            return None
        return {
            "http_status": data.get("http_status"),
            "api_status": data.get("api_status"),
            "error": data.get("error"),
            "get_channel_status": data.get("api_status_get_channel"),
            "get_ndi_sources_status": data.get("api_status_get_ndi_sources"),
            "list_channels_status": data.get("api_status_list_channels"),
            "get_signal_info_status": data.get("api_status_get_signal_info"),
            "auth_configured": data.get("auth_configured"),
            "auth_required_by_device": data.get("auth_required_by_device"),
        }
