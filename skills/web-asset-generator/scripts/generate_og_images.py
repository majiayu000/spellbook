#!/usr/bin/env python3
"""Generate Open Graph and social sharing images."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageColor, ImageDraw, ImageFont


OUTPUTS = {
    "og-image.png": (1200, 630),
    "twitter-image.png": (1200, 675),
    "og-square.png": (1200, 1200),
}


def parse_og_color(value: str) -> tuple[int, int, int]:
    try:
        color = ImageColor.getrgb(value)
    except ValueError as exc:
        raise ValueError(f"invalid color: {value}") from exc
    return color[:3]


def load_og_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def fit_logo(path: Path, max_size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image


def paste_center(canvas: Image.Image, image: Image.Image, y_offset: int = 0) -> None:
    x = (canvas.width - image.width) // 2
    y = (canvas.height - image.height) // 2 + y_offset
    canvas.alpha_composite(image, (x, y))


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def split_long_word(draw: ImageDraw.ImageDraw, word: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    parts = []
    current = ""
    for char in word:
        candidate = current + char
        if current and text_width(draw, candidate, font) > max_width:
            parts.append(current)
            current = char
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        if not words:
            continue
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if text_width(draw, candidate, font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            if text_width(draw, word, font) <= max_width:
                current = word
            else:
                parts = split_long_word(draw, word, font, max_width)
                lines.extend(parts[:-1])
                current = parts[-1]
        if current:
            lines.append(current)
    return lines


def draw_wrapped_text(canvas: Image.Image, text: str, color: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(canvas)
    max_width = round(canvas.width * 0.82)
    max_height = round(canvas.height * 0.66)
    max_lines = 5
    start_size = 76 if canvas.width > canvas.height else 88
    min_size = 36 if canvas.width > canvas.height else 44
    chosen = None
    for size in range(start_size, min_size - 1, -4):
        font = load_og_font(size, bold=True)
        lines = wrap_to_width(draw, text, font, max_width)
        gap = max(12, round(size * 0.28))
        heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
        total_height = sum(heights) + (len(lines) - 1) * gap
        if lines and len(lines) <= max_lines and total_height <= max_height:
            chosen = (font, lines, heights, gap, total_height)
            break
    if chosen is None:
        raise ValueError("text is too long to fit social images without truncation")
    font, lines, line_heights, gap, total_height = chosen
    y = (canvas.height - total_height) // 2
    for line, line_height in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (canvas.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_height + gap


def make_image(
    size: tuple[int, int],
    *,
    source_image: Path | None,
    text: str | None,
    logo: Path | None,
    bg_color: tuple[int, int, int],
    text_color: tuple[int, int, int],
) -> Image.Image:
    canvas = Image.new("RGBA", size, (*bg_color, 255))
    if source_image and not text:
        paste_center(canvas, fit_logo(source_image, (round(size[0] * 0.62), round(size[1] * 0.62))))
        return canvas
    if logo:
        logo_image = fit_logo(logo, (round(size[0] * 0.18), round(size[1] * 0.18)))
        paste_center(canvas, logo_image, y_offset=round(-size[1] * 0.24))
    if text:
        draw_wrapped_text(canvas, text, text_color)
    return canvas


def write_meta_tags(output_dir: Path) -> None:
    tags = """<meta property="og:image" content="/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="/twitter-image.png">
"""
    (output_dir / "meta-tags.txt").write_text(tags, encoding="utf-8")


def validate_og_images(output_dir: Path) -> None:
    errors = []
    for filename, size in OUTPUTS.items():
        path = output_dir / filename
        if not path.exists():
            errors.append(f"missing {filename}")
            continue
        with Image.open(path) as image:
            if image.size != size:
                errors.append(f"{filename} has size {image.size}, expected {size}")
    if not (output_dir / "meta-tags.txt").exists():
        errors.append("missing meta-tags.txt")
    if errors:
        raise ValueError("validation failed: " + "; ".join(errors))


def relative_luminance(color: tuple[int, int, int]) -> float:
    channels = []
    for channel in color:
        value = channel / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    l1 = relative_luminance(first)
    l2 = relative_luminance(second)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def validate_text_contrast(bg_color: tuple[int, int, int], text_color: tuple[int, int, int]) -> None:
    ratio = contrast_ratio(bg_color, text_color)
    if ratio < 4.5:
        raise ValueError(f"text contrast ratio {ratio:.2f}:1 is below WCAG AA minimum 4.5:1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    parser.add_argument("--image", help="Logo or source image to center in social images")
    parser.add_argument("--text", help="Text or slogan to render")
    parser.add_argument("--logo", help="Optional logo to include above text")
    parser.add_argument("--bg-color", default="#4F46E5")
    parser.add_argument("--text-color", default="white")
    parser.add_argument("--validate", action="store_true", help="Validate generated files and dimensions")
    args = parser.parse_args()

    if not args.image and not args.text:
        print("error: provide --image or --text", file=sys.stderr)
        return 1

    try:
        bg_color = parse_og_color(args.bg_color)
        text_color = parse_og_color(args.text_color)
        if args.validate and args.text:
            validate_text_contrast(bg_color, text_color)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_image = Path(args.image) if args.image else None
    logo = Path(args.logo) if args.logo else source_image if args.text and args.image else None

    try:
        for filename, size in OUTPUTS.items():
            image = make_image(
                size,
                source_image=source_image,
                text=args.text,
                logo=logo,
                bg_color=bg_color,
                text_color=text_color,
            )
            path = output_dir / filename
            image.convert("RGB").save(path, quality=92)
            print(path)
        write_meta_tags(output_dir)
        if args.validate:
            validate_og_images(output_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
