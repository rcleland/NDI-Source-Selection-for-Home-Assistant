"""Shared entity base for Magewell decoder entities."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MagewellDecoderCoordinator


class MagewellEntity(CoordinatorEntity[MagewellDecoderCoordinator]):
    """Common availability and device info."""

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return data is not None and bool(data.get("reachable"))

    @property
    def device_info(self):
        return self.coordinator.device_info
