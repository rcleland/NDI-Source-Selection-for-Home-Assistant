"""Select entity: choose NDI or preset decode source."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .coordinator import MagewellDecoderCoordinator
from .entity import MagewellEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: MagewellDecoderCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MagewellDecoderSourceSelect(coordinator)])


class MagewellDecoderSourceSelect(MagewellEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "decode_source"

    def __init__(self, coordinator: MagewellDecoderCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_decode_source"

    @property
    def options(self) -> list[str]:
        data = self.coordinator.data
        return list(data.get("select_options") or []) if data else []

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        return data.get("current_select_option") if data else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_select_source(option)
