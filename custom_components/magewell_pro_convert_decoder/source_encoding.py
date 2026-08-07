"""Encode/decode select options for Magewell set-channel (NDI vs preset)."""

from __future__ import annotations

NDI_PREFIX = "[NDI] "
PRESET_PREFIX = "[Preset] "


def encode_source_option(is_ndi: bool, name: str) -> str:
    """Build option string shown in UI and stored by scenes."""
    return (NDI_PREFIX if is_ndi else PRESET_PREFIX) + name


def decode_source_option(option: str) -> tuple[bool, str]:
    """Return (is_ndi, source_name) for mwapi set-channel."""
    if option.startswith(NDI_PREFIX):
        return True, option[len(NDI_PREFIX) :]
    if option.startswith(PRESET_PREFIX):
        return False, option[len(PRESET_PREFIX) :]
    msg = "Invalid source option"
    raise ValueError(msg)
