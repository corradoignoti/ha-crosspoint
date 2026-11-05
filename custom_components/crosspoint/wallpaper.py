"""Convert images into CrossPoint sleep screens (blocking helpers).

Normal mode produces an uncompressed 24-bit BMP. Transparent mode produces a
PNG with an alpha channel, drawn by the firmware on top of the current
screen. Both are resized and cropped to the model resolution, converted to
grayscale and dithered to the gray levels of the e-paper display.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from PIL import Image, ImageOps

MODE_NORMAL = "normal"
MODE_TRANSPARENT = "transparent"
MODES = (MODE_NORMAL, MODE_TRANSPARENT)

# Gray levels rendered by the e-paper panel.
GRAY_LEVELS = 4
# Refuse absurdly large sources before decoding them fully.
MAX_SOURCE_PIXELS = 64_000_000


class WallpaperError(Exception):
    """The source file cannot be converted."""


@dataclass(frozen=True, slots=True)
class Wallpaper:
    """A converted sleep screen."""

    data: bytes
    extension: str  # ".bmp" or ".png"
    has_transparency: bool  # whether the source has any transparent pixel


def _open(source: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(source))
        if img.width * img.height > MAX_SOURCE_PIXELS:
            raise WallpaperError("Image is too large")
        img.load()
    except (OSError, ValueError, Image.DecompressionBombError) as err:
        raise WallpaperError(f"Cannot read image: {err}") from err
    img = ImageOps.exif_transpose(img)
    # Normalize palette or grayscale transparency into a real alpha channel.
    if img.mode in ("P", "PA", "LA", "L", "1", "I", "I;16", "F", "CMYK", "YCbCr"):
        has_alpha = img.mode in ("PA", "LA") or "transparency" in img.info
        img = img.convert("RGBA" if has_alpha else "RGB")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    return img


def has_transparency(img: Image.Image) -> bool:
    """Return True if at least one pixel is not fully opaque."""
    if img.mode != "RGBA":
        return False
    low, _ = img.getchannel("A").getextrema()
    return low < 255


def check_transparency(source: bytes) -> bool:
    """Return True if the source image has transparent pixels."""
    return has_transparency(_open(source))


def _dither_gray(img: Image.Image, levels: int) -> Image.Image:
    """Floyd-Steinberg dither an image to ``levels`` evenly spaced grays."""
    step = 255 / (levels - 1)
    grays = [round(i * step) for i in range(levels)]
    palette = Image.new("P", (1, 1))
    palette.putpalette([v for g in grays for v in (g, g, g)] * (256 // levels))
    gray = img.convert("L").convert("RGB")
    return gray.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG).convert(
        "L"
    )


def convert(
    source: bytes, size: tuple[int, int], mode: str, *, levels: int = GRAY_LEVELS
) -> Wallpaper:
    """Convert a source image into a sleep screen of ``size`` (width, height)."""
    if mode not in MODES:
        raise ValueError(f"Unknown wallpaper mode: {mode}")
    img = _open(source)
    transparent = has_transparency(img)
    fitted = ImageOps.fit(img, size, Image.Resampling.LANCZOS)

    out = io.BytesIO()
    if mode == MODE_NORMAL:
        if fitted.mode == "RGBA":
            background = Image.new("RGBA", size, (255, 255, 255, 255))
            fitted = Image.alpha_composite(background, fitted)
        # Pillow writes RGB images as uncompressed 24-bit BMP.
        _dither_gray(fitted, levels).convert("RGB").save(out, "BMP")
        return Wallpaper(out.getvalue(), ".bmp", transparent)

    alpha = (
        fitted.getchannel("A") if fitted.mode == "RGBA" else Image.new("L", size, 255)
    )
    gray = _dither_gray(fitted.convert("RGB"), levels)
    result = Image.merge("RGBA", (gray, gray, gray, alpha))
    result.save(out, "PNG", optimize=True)
    return Wallpaper(out.getvalue(), ".png", transparent)


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def device_filename(stem: str, sha256: str, extension: str) -> str:
    """Return a device-safe, collision-free file name for a converted image.

    The source hash is part of the name, so two sources with the same stem
    never overwrite each other and a modified source gets a new file.
    """
    safe = _UNSAFE.sub("_", stem).strip("._") or "wallpaper"
    return f"{safe[:48]}-{sha256[:8]}{extension}"
