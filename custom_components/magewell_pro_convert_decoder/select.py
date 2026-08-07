"""Select entity: choose NDI or preset decode source (scene-friendly)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MagewellDecoderCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: MagewellDecoderCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MagewellDecoderSourceSelect(coordinator)])


class MagewellDecoderSourceSelect(
    CoordinatorEntity[MagewellDecoderCoordinator], SelectEntity
):
    """Select discovered NDI sources and preset channels (set-channel API)."""

    _attr_has_entity_name = True
    _attr_translation_key = "decode_source"

    def __init__(self, coordinator: MagewellDecoderCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_decode_source"

    @property
    def options(self) -> list[str]:
        data = self.coordinator.data
        if not data:
            return []
        return list(data.get("select_options") or [])

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("current_select_option")

    @property
    def available(self) -> bool:
        if self.coordinator.data is None:
            return False
        return bool(self.coordinator.data.get("reachable"))

    @property
    def device_info(self):
        return self.coordinator.device_info

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_select_source(option)
