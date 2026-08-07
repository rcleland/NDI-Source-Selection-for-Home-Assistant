"""Sensors: current source name, video aspect ratio, frame rate (field-rate)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_normalize import ndi_display_name, ndi_source_address, video_aspect_ratio, video_field_rate
from .const import DOMAIN
from .coordinator import MagewellDecoderCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: MagewellDecoderCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MagewellSourceNameSensor(coordinator),
            MagewellAspectRatioSensor(coordinator),
            MagewellFrameRateSensor(coordinator),
        ]
    )


class _MagewellSensor(CoordinatorEntity[MagewellDecoderCoordinator], SensorEntity):
    """Explicit _attr_name on subclasses so UI shows a label, not only device + state."""

    @property
    def available(self) -> bool:
        if self.coordinator.data is None:
            return False
        return bool(self.coordinator.data.get("reachable"))

    @property
    def device_info(self):
        return self.coordinator.device_info


class MagewellSourceNameSensor(_MagewellSensor):
    """Source name from get-channel."""

    _attr_has_entity_name = False
    _attr_name = "Active source name"

    def __init__(self, coordinator: MagewellDecoderCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_source_name"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        src = data.get("current_source")
        if not src:
            return None
        return str(src.get("name", "")) or None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data:
            return None
        src = data.get("current_source")
        if not src:
            return None
        attrs: dict[str, Any] = {"ndi_source": src.get("ndi_name")}
        if src.get("ndi_name"):
            for item in data.get("ndi_sources") or []:
                if isinstance(item, dict) and ndi_display_name(item) == src.get("name"):
                    addr = ndi_source_address(item)
                    if addr:
                        attrs["ip_addr"] = addr
                    break
        return attrs


class MagewellAspectRatioSensor(_MagewellSensor):
    """aspect-ratio from get-signal-info video-info."""

    _attr_has_entity_name = False
    _attr_name = "Video aspect ratio"

    def __init__(self, coordinator: MagewellDecoderCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_aspect_ratio"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        vi = data.get("video_info")
        if not isinstance(vi, dict):
            return None
        ar = video_aspect_ratio(vi)
        return str(ar) if ar is not None else None


class MagewellFrameRateSensor(_MagewellSensor):
    """field-rate from get-signal-info video-info (displayed as fps)."""

    _attr_has_entity_name = False
    _attr_name = "Video frame rate"
    _attr_native_unit_of_measurement = "fps"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: MagewellDecoderCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_video_frame_rate"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        vi = data.get("video_info")
        if not isinstance(vi, dict):
            return None
        return video_field_rate(vi)
