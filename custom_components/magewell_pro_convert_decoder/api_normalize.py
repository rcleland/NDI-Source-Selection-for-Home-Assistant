"""Normalize Magewell mwapi JSON (docs use kebab-case; firmware may differ)."""

from __future__ import annotations

from typing import Any


def first_str(obj: dict[str, Any], *keys: str) -> str | None:
    """First non-empty string for any of the given keys."""
    for key in keys:
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def first_dict(obj: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    """First dict value for any of the given keys."""
    for key in keys:
        val = obj.get(key)
        if isinstance(val, dict) and val:
            return val
    return None


def as_bool(val: Any) -> bool:
    """Coerce JSON/firmware boolean-ish values."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on")
    return bool(val)


def ndi_display_name(entry: dict[str, Any]) -> str | None:
    """Resolved NDI source label from a get-ndi-sources row."""
    return first_str(
        entry,
        "ndi-name",
        "ndi_name",
        "ndiName",
        "name",
        "label",
    )


def ndi_source_address(entry: dict[str, Any]) -> str | None:
    """IP:port or host:port for ntkndi URL `url` parameter."""
    return first_str(
        entry,
        "ip-addr",
        "ip_addr",
        "ipAddr",
        "address",
        "url",
    )


def normalize_ndi_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source dicts from get-ndi-sources response."""
    raw = payload.get("sources")
    if not isinstance(raw, list):
        for alt in ("ndi-sources", "ndi_sources", "NDISources", "data"):
            r = payload.get(alt)
            if isinstance(r, list):
                raw = r
                break
        else:
            return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
    return out


def normalize_preset_channels(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return channels from list-channels."""
    raw = payload.get("channels")
    if not isinstance(raw, list):
        for alt in ("channel", "preset", "presets"):
            r = payload.get(alt)
            if isinstance(r, list):
                raw = r
                break
        else:
            return []
    return [x for x in raw if isinstance(x, dict)]


def parse_current_channel(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Parse get-channel body."""
    raw_name = payload.get("name")
    if raw_name is None:
        raw_name = first_str(payload, "Name", "channel", "channel-name", "channel_name")
    if raw_name is None:
        return None
    name = str(raw_name).strip() or None
    if not name:
        return None
    ndi_raw = payload.get("ndi-name")
    if ndi_raw is None:
        ndi_raw = payload.get("ndi_name", payload.get("ndiName"))
    return {"name": name, "ndi_name": as_bool(ndi_raw)}


def extract_video_info(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Video block from get-signal-info."""
    block = first_dict(payload, "video-info", "video_info", "videoInfo")
    if block is not None:
        return block
    return None


def video_aspect_ratio(video: dict[str, Any]) -> str | None:
    return first_str(video, "aspect-ratio", "aspect_ratio", "aspectRatio")


def video_field_rate(video: dict[str, Any]) -> float | None:
    for key in ("field-rate", "field_rate", "fieldRate", "frame-rate", "frame_rate"):
        val = video.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None
