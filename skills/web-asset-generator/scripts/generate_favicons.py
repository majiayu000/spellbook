#!/usr/bin/env python3
"""Generate favicons and PWA app icons from an image, emoji, or text."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageColor, ImageDraw, ImageFont


FAVICON_SIZES = {
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "favicon-96x96.png": 96,
}

APP_SIZES = {
    "apple-touch-icon.png": 180,
    "android-chrome-192x192.png": 192,
    "android-chrome-512x512.png": 512,
}

SUGGESTIONS = {
    "coffee": [("☕", "Coffee"), ("🌐", "Globe"), ("🏪", "Store"), ("🛒", "Cart")],
    "shop": [("🛒", "Cart"), ("🏪", "Store"), ("💳", "Payment"), ("✨", "Sparkle")],
    "ai": [("✨", "Sparkle"), ("🤖", "Robot"), ("⚡", "Lightning"), ("🧠", "Brain")],
    "code": [("💻", "Laptop"), ("⚙️", "Gear"), ("🚀", "Rocket"), ("🧩", "Puzzle")],
    "health": [("💚", "Heart"), ("➕", "Plus"), ("🌿", "Leaf"), ("🩺", "Stethoscope")],
}


def parse_color(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    if value == "transparent":
        return (0, 0, 0, 0)
    try:
        rgb = ImageColor.getrgb(value)
    except ValueError as exc:
        raise ValueError(f"invalid color: {value}") from exc
    if len(rgb) == 4:
        return rgb
    return (*rgb, 255)


def square_canvas(size: int, background: tuple[int, int, int, int]) -> Image.Image:
    return Image.new("RGBA", (size, size), background)


def fit_image(source: Image.Image, size: int, background: tuple[int, int, int, int]) -> Image.Image:
    canvas = square_canvas(size, background)
    image = source.convert("RGBA")
    image.thumbnail((round(size * 0.82), round(size * 0.82)), Image.Resampling.LANCZOS)
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    return canvas


def emoji_image(emoji: str, size: int, background: tuple[int, int, int, int]) -> Image.Image:
    canvas = square_canvas(size, background)
    draw = ImageDraw.Draw(canvas)
    font = load_font(round(size * 0.62))
    bbox = draw.textbbox((0, 0), emoji, font=font)
    x = (size - (bbox[2] - bbox[0])) / 2 - bbox[0]
    y = (size - (bbox[3] - bbox[1])) / 2 - bbox[1]
    try:
        from pilmoji import Pilmoji
    except ImportError:
        draw.text((x, y), emoji, font=font, fill=(17, 24, 39, 255))
    else:
        with Pilmoji(canvas) as pilmoji:
            pilmoji.text((x, y), emoji, font=font, fill=(17, 24, 39, 255))
    return canvas


def text_image(
    text: str,
    size: int,
    background: tuple[int, int, int, int],
    text_color: tuple[int, int, int, int],
) -> Image.Image:
    canvas = square_canvas(size, background)
    draw = ImageDraw.Draw(canvas)
    font = load_text_font(round(size * (0.54 if len(text.strip()) <= 2 else 0.44)))
    label = text.strip()[:4].upper()
    bbox = draw.textbbox((0, 0), label, font=font)
    x = (size - (bbox[2] - bbox[0])) / 2 - bbox[0]
    y = (size - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((x, y), label, font=font, fill=text_color)
    return canvas


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def load_text_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def icon_sizes(icon_type: str) -> dict[str, int]:
    if icon_type == "favicon":
        return FAVICON_SIZES
    if icon_type == "app":
        return APP_SIZES
    if icon_type == "all":
        return {**FAVICON_SIZES, **APP_SIZES}
    raise ValueError("icon_type must be one of: favicon, app, all")


def default_emoji_background(filename: str, requested: tuple[int, int, int, int] | None) -> tuple[int, int, int, int]:
    if requested is not None:
        return requested
    if filename in APP_SIZES:
        return (255, 255, 255, 255)
    return (0, 0, 0, 0)


def default_text_background(filename: str, requested: tuple[int, int, int, int] | None) -> tuple[int, int, int, int]:
    if requested is not None:
        return requested
    if filename in APP_SIZES:
        return (255, 255, 255, 255)
    return (0, 0, 0, 0)


def generate_icons(
    output_dir: Path,
    icon_type: str,
    source: Image.Image | None,
    emoji: str | None,
    text: str | None,
    background: tuple[int, int, int, int] | None,
    text_color: tuple[int, int, int, int],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    images_for_ico = []
    for filename, size in icon_sizes(icon_type).items():
        if emoji:
            image = emoji_image(emoji, size, default_emoji_background(filename, background))
        elif text:
            image = text_image(text, size, default_text_background(filename, background), text_color)
        elif source:
            image = fit_image(source, size, background or (0, 0, 0, 0))
        else:
            raise ValueError("provide source image, --emoji, or --text")
        path = output_dir / filename
        image.save(path)
        written.append(path)
        if filename.startswith("favicon-"):
            images_for_ico.append(image)
    if icon_type in {"favicon", "all"} and images_for_ico:
        ico_path = output_dir / "favicon.ico"
        images_for_ico[-1].save(ico_path, sizes=[(image.width, image.height) for image in images_for_ico])
        written.append(ico_path)
    write_tags(output_dir, icon_type)
    return written


def write_tags(output_dir: Path, icon_type: str) -> None:
    tags = []
    if icon_type in {"favicon", "all"}:
        tags.extend(
            [
                '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">',
                '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">',
                '<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png">',
                '<link rel="shortcut icon" href="/favicon.ico">',
            ]
        )
    if icon_type in {"app", "all"}:
        tags.extend(
            [
                '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">',
                '<link rel="manifest" href="/site.webmanifest">',
            ]
        )
    manifest = """{
  "icons": [
    { "src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
"""
    (output_dir / "html-tags.txt").write_text("\n".join(tags) + "\n", encoding="utf-8")
    if icon_type in {"app", "all"}:
        (output_dir / "site.webmanifest").write_text(manifest, encoding="utf-8")


def validate_icons(output_dir: Path, icon_type: str) -> None:
    errors = []
    for filename, size in icon_sizes(icon_type).items():
        path = output_dir / filename
        if not path.exists():
            errors.append(f"missing {filename}")
            continue
        with Image.open(path) as image:
            if image.size != (size, size):
                errors.append(f"{filename} has size {image.size}, expected {(size, size)}")
    if icon_type in {"favicon", "all"} and not (output_dir / "favicon.ico").exists():
        errors.append("missing favicon.ico")
    if not (output_dir / "html-tags.txt").exists():
        errors.append("missing html-tags.txt")
    if icon_type in {"app", "all"} and not (output_dir / "site.webmanifest").exists():
        errors.append("missing site.webmanifest")
    if errors:
        raise ValueError("validation failed: " + "; ".join(errors))


def suggest_emojis(description: str) -> None:
    haystack = description.lower()
    choices = []
    for keyword, suggestions in SUGGESTIONS.items():
        if keyword in haystack:
            choices.extend(suggestions)
    if not choices:
        choices = [("🌐", "Globe"), ("✨", "Sparkle"), ("🚀", "Rocket"), ("💡", "Idea")]
    seen = set()
    for index, (emoji, label) in enumerate([item for item in choices if not (item in seen or seen.add(item))][:4], 1):
        print(f"{index}. {emoji}  {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--suggest", help="Print emoji suggestions for a project description")
    parser.add_argument("--emoji", help="Generate icons from this emoji")
    parser.add_argument("--emoji-bg", default=None, help="Background color for emoji icons")
    parser.add_argument("--text", help="Generate icons from text or initials")
    parser.add_argument("--text-bg", default=None, help="Background color for text icons")
    parser.add_argument("--text-color", default="#111827", help="Text color for text icons")
    parser.add_argument("--validate", action="store_true", help="Validate generated files and dimensions")
    args = parser.parse_args()

    if args.suggest:
        suggest_emojis(args.suggest)
        return 0

    try:
        if args.emoji and args.text:
            raise ValueError("use either --emoji or --text, not both")
        if args.emoji:
            if not args.paths:
                raise ValueError("output_dir is required when using --emoji")
            output_dir = Path(args.paths[0])
            icon_type = args.paths[1] if len(args.paths) > 1 else "all"
            background = parse_color(args.emoji_bg)
            written = generate_icons(output_dir, icon_type, None, args.emoji, None, background, (17, 24, 39, 255))
        elif args.text:
            if not args.paths:
                raise ValueError("output_dir is required when using --text")
            output_dir = Path(args.paths[0])
            icon_type = args.paths[1] if len(args.paths) > 1 else "all"
            background = parse_color(args.text_bg)
            text_color = parse_color(args.text_color)
            if text_color is None:
                raise ValueError("text color is required")
            written = generate_icons(output_dir, icon_type, None, None, args.text, background, text_color)
        else:
            if len(args.paths) < 2:
                raise ValueError("usage: generate_favicons.py <source_image> <output_dir> [icon_type]")
            source_image = Image.open(args.paths[0])
            output_dir = Path(args.paths[1])
            icon_type = args.paths[2] if len(args.paths) > 2 else "all"
            written = generate_icons(output_dir, icon_type, source_image, None, None, (0, 0, 0, 0), (17, 24, 39, 255))
        if args.validate:
            validate_icons(output_dir, icon_type)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
