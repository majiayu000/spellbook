#!/usr/bin/env python3
"""Generate basic design system tokens from a brand color."""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys


STYLE_PRESETS = {
    "modern": {
        "font_body": "Inter, ui-sans-serif, system-ui, sans-serif",
        "font_display": "Inter, ui-sans-serif, system-ui, sans-serif",
        "radius": "8px",
        "shadow": "0 12px 32px rgba(15, 23, 42, 0.12)",
    },
    "classic": {
        "font_body": "Georgia, ui-serif, serif",
        "font_display": "Georgia, ui-serif, serif",
        "radius": "4px",
        "shadow": "0 8px 24px rgba(30, 41, 59, 0.10)",
    },
    "playful": {
        "font_body": "Nunito, ui-sans-serif, system-ui, sans-serif",
        "font_display": "Nunito, ui-sans-serif, system-ui, sans-serif",
        "radius": "16px",
        "shadow": "0 16px 36px rgba(88, 28, 135, 0.16)",
    },
}


def parse_hex_color(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", value.strip())
    if not match:
        raise ValueError("brand_color must be a 6-digit hex color, for example #2563eb")
    raw = match.group(1)
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(channel * 255))):02x}" for channel in rgb)


def color_scale(brand_rgb: tuple[int, int, int]) -> dict[str, str]:
    hue, _, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in brand_rgb))
    scale_saturation = 0.0 if saturation < 0.02 else min(0.95, saturation)
    brand_hex = "#" + "".join(f"{channel:02x}" for channel in brand_rgb)
    stops = {
        "50": 0.97,
        "100": 0.92,
        "200": 0.84,
        "300": 0.74,
        "400": 0.64,
        "500": 0.52,
        "600": 0.44,
        "700": 0.34,
        "800": 0.24,
        "900": 0.16,
    }
    scale = {
        key: to_hex(colorsys.hls_to_rgb(hue, lightness, scale_saturation))
        for key, lightness in stops.items()
    }
    scale["500"] = brand_hex
    return scale


def build_tokens(brand_color: str, style: str) -> dict[str, object]:
    preset = STYLE_PRESETS[style]
    colors = color_scale(parse_hex_color(brand_color))
    return {
        "color": {
            "brand": colors,
            "semantic": {
                "background": "#ffffff",
                "foreground": "#111827",
                "muted": "#f3f4f6",
                "border": "#d1d5db",
                "success": "#16a34a",
                "warning": "#d97706",
                "danger": "#dc2626",
            },
        },
        "typography": {
            "fontFamily": {
                "body": preset["font_body"],
                "display": preset["font_display"],
            },
            "fontSize": {
                "xs": "0.75rem",
                "sm": "0.875rem",
                "base": "1rem",
                "lg": "1.125rem",
                "xl": "1.25rem",
                "2xl": "1.5rem",
                "3xl": "1.875rem",
            },
        },
        "space": {str(step): f"{step * 0.5}rem" for step in range(0, 13)},
        "radius": {
            "sm": "4px",
            "md": preset["radius"],
            "lg": "calc(" + preset["radius"] + " * 1.5)",
        },
        "shadow": {
            "sm": "0 1px 2px rgba(15, 23, 42, 0.08)",
            "md": preset["shadow"],
        },
        "animation": {
            "duration": {
                "instant": "0ms",
                "fast": "150ms",
                "normal": "250ms",
                "slow": "400ms",
            },
            "easing": {
                "standard": "cubic-bezier(0.2, 0, 0, 1)",
                "enter": "cubic-bezier(0, 0, 0.2, 1)",
                "exit": "cubic-bezier(0.4, 0, 1, 1)",
            },
        },
        "breakpoint": {
            "sm": "640px",
            "md": "768px",
            "lg": "1024px",
            "xl": "1280px",
        },
    }


def flatten(prefix: str, value: object) -> dict[str, str]:
    if isinstance(value, dict):
        output: dict[str, str] = {}
        for key, nested in value.items():
            output.update(flatten(f"{prefix}-{key}" if prefix else str(key), nested))
        return output
    return {prefix: str(value)}


def render_css(tokens: dict[str, object], scss: bool = False) -> str:
    flat = flatten("", tokens)
    if scss:
        return "\n".join(f"${key}: {value};" for key, value in flat.items())
    lines = [":root {"]
    lines.extend(f"  --{key}: {value};" for key, value in flat.items())
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brand_color", help="6-digit hex color, for example #2563eb")
    parser.add_argument("style", choices=sorted(STYLE_PRESETS), help="Visual style preset")
    parser.add_argument("format", choices=["json", "css", "scss"], help="Output format")
    args = parser.parse_args()

    try:
        tokens = build_tokens(args.brand_color, args.style)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(tokens, indent=2))
    elif args.format == "scss":
        print(render_css(tokens, scss=True))
    else:
        print(render_css(tokens))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
