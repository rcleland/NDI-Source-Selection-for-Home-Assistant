#!/usr/bin/env python3
"""Generate brand PNG assets without third-party dependencies."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components/magewell_pro_convert_decoder/brand"
DOCS = ROOT / "docs/brand"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def bg_color(y: float, height: float) -> tuple[int, int, int]:
    t = y / max(height - 1, 1)
    return (
        int(lerp(16, 8, t)),
        int(lerp(44, 130, t)),
        int(lerp(88, 155, t)),
    )


def inside_round_rect(x: float, y: float, w: float, h: float, r: float) -> bool:
    if x < 0 or y < 0 or x >= w or y >= h:
        return False
    r = min(r, w / 2, h / 2)
    if x < r and y < r:
        return (x - r) ** 2 + (y - r) ** 2 <= r * r
    if x > w - r and y < r:
        return (x - (w - r)) ** 2 + (y - r) ** 2 <= r * r
    if x < r and y > h - r:
        return (x - r) ** 2 + (y - (h - r)) ** 2 <= r * r
    if x > w - r and y > h - r:
        return (x - (w - r)) ** 2 + (y - (h - r)) ** 2 <= r * r
    return True


def dist_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def point_in_triangle(px: float, py: float, ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    def sign(x1, y1, x2, y2, x3, y3):
        return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)

    b1 = sign(px, py, ax, ay, bx, by) < 0.0
    b2 = sign(px, py, bx, by, cx, cy) < 0.0
    b3 = sign(px, py, cx, cy, ax, ay) < 0.0
    return b1 == b2 == b3


def render_icon(size: int, dark: bool = False) -> list[tuple[int, int, int, int]]:
    pixels: list[tuple[int, int, int, int]] = []
    pad = size * 0.16
    screen = (pad, pad * 1.05, size - pad, size - pad * 1.55)
    for y in range(size):
        for x in range(size):
            if not inside_round_rect(x + 0.5, y + 0.5, size, size, size * 0.22):
                pixels.append((0, 0, 0, 0))
                continue
            r, g, b = bg_color(y, size)
            if dark:
                r = min(255, r + 12)
                g = min(255, g + 12)
                b = min(255, b + 12)
            a = 255

            sx0, sy0, sx1, sy1 = screen
            if inside_round_rect(x + 0.5 - sx0, y + 0.5 - sy0, sx1 - sx0, sy1 - sy0, size * 0.05):
                r, g, b = 255, 255, 255
                a = 70

            stand_w = size * 0.28
            stand_h = size * 0.07
            stand_x0 = (size - stand_w) / 2
            stand_y0 = sy1 + pad * 0.15
            if inside_round_rect(x + 0.5 - stand_x0, y + 0.5 - stand_y0, stand_w, stand_h, size * 0.02):
                r, g, b = 255, 255, 255

            cy = (sy0 + sy1) / 2
            for y_off in (-0.12, 0.0, 0.12):
                ly = cy + size * y_off
                if dist_segment(x + 0.5, y + 0.5, pad * 0.35, ly, sx0 - pad * 0.15, ly) <= max(2, size / 48):
                    r, g, b = 120, 220, 255
                if math.hypot(x + 0.5 - pad * 0.35, y + 0.5 - ly) <= size * 0.02:
                    r, g, b = 180, 230, 240
                if point_in_triangle(
                    x + 0.5,
                    y + 0.5,
                    sx0 - pad * 0.15,
                    ly,
                    sx0 - pad * 0.15 - size * 0.05,
                    ly - size * 0.035,
                    sx0 - pad * 0.15 - size * 0.05,
                    ly + size * 0.035,
                ):
                    r, g, b = 120, 220, 255

            cx = (sx0 + sx1) / 2
            cy2 = (sy0 + sy1) / 2
            tri = size * 0.09
            if point_in_triangle(
                x + 0.5,
                y + 0.5,
                cx - tri * 0.35,
                cy2 - tri,
                cx - tri * 0.35,
                cy2 + tri,
                cx + tri * 0.85,
                cy2,
            ):
                r, g, b = 255, 255, 255

            badge_w = size * 0.22
            badge_h = size * 0.08
            bx0 = sx1 - badge_w - pad * 0.15
            by0 = sy1 - badge_h - pad * 0.1
            if inside_round_rect(x + 0.5 - bx0, y + 0.5 - by0, badge_w, badge_h, size * 0.02):
                r, g, b = 210, 240, 250

            pixels.append((r, g, b, a))
    return pixels


def render_logo(width: int, height: int) -> list[tuple[int, int, int, int]]:
    icon_size = int(height * 0.78)
    icon = render_icon(icon_size)
    pixels: list[tuple[int, int, int, int]] = []
    offset_x = int(height * 0.08)
    offset_y = int((height - icon_size) / 2)
    for y in range(height):
        for x in range(width):
            if offset_x <= x < offset_x + icon_size and offset_y <= y < offset_y + icon_size:
                pixels.append(icon[(y - offset_y) * icon_size + (x - offset_x)])
            else:
                pixels.append((255, 255, 255, 0))
    return pixels


def write_png(path: Path, width: int, height: int, rgba: list[tuple[int, int, int, int]]) -> None:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            r, g, b, a = rgba[y * width + x]
            raw.extend((r, g, b, a))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def main() -> None:
    assets = {
        "icon.png": (256, 256, render_icon(256)),
        "icon@2x.png": (512, 512, render_icon(512)),
        "dark_icon.png": (256, 256, render_icon(256, dark=True)),
        "dark_icon@2x.png": (512, 512, render_icon(512, dark=True)),
        "logo.png": (512, 256, render_logo(512, 256)),
        "logo@2x.png": (1024, 512, render_logo(1024, 512)),
    }
    for name, (w, h, px) in assets.items():
        for base in (BRAND, DOCS):
            out = base / name
            write_png(out, w, h, px)
            print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
