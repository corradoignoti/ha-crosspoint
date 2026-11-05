"""Tests for the wallpaper conversion pipeline."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from custom_components.crosspoint.wallpaper import (
    MODE_NORMAL,
    MODE_TRANSPARENT,
    WallpaperError,
    check_transparency,
    convert,
    device_filename,
)

SIZE = (480, 800)


def _image(mode: str, size=(1000, 1000), color=(200, 30, 30, 128), fmt="PNG"):
    out = io.BytesIO()
    Image.new(mode, size, color[: len(mode)] if mode != "L" else 120).save(out, fmt)
    return out.getvalue()


def _open(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def test_normal_is_24bit_bmp_with_dithered_grays():
    result = convert(_image("RGB", (1600, 900)), SIZE, MODE_NORMAL)
    img = _open(result.data)
    assert result.extension == ".bmp"
    assert img.format == "BMP"
    assert img.mode == "RGB"  # 24-bit
    assert img.size == SIZE
    assert result.data[30:34] == b"\x00\x00\x00\x00"  # BI_RGB: uncompressed
    colors = {color for _, color in img.getcolors()}
    assert colors <= {(v, v, v) for v in (0, 85, 170, 255)}
    assert result.has_transparency is False


def test_transparent_keeps_alpha():
    source = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    source.paste((20, 20, 20, 255), (100, 100, 400, 400))
    buf = io.BytesIO()
    source.save(buf, "PNG")

    result = convert(buf.getvalue(), SIZE, MODE_TRANSPARENT)
    img = _open(result.data)
    assert result.extension == ".png"
    assert img.mode == "RGBA"
    assert img.size == SIZE
    assert result.has_transparency is True
    assert img.getchannel("A").getextrema() == (0, 255)


def test_transparent_mode_on_opaque_image():
    result = convert(_image("RGB"), SIZE, MODE_TRANSPARENT)
    assert result.has_transparency is False
    assert _open(result.data).getchannel("A").getextrema() == (255, 255)


def test_normal_flattens_alpha_on_white():
    result = convert(_image("RGBA", color=(0, 0, 0, 0)), SIZE, MODE_NORMAL)
    assert _open(result.data).getcolors() == [(SIZE[0] * SIZE[1], (255, 255, 255))]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("RGB", False), ("RGBA", True), ("L", False)],
)
def test_check_transparency(mode, expected):
    assert check_transparency(_image(mode)) is expected


def test_palette_transparency_detected():
    img = Image.new("P", (10, 10), 0)
    buf = io.BytesIO()
    img.save(buf, "PNG", transparency=0)
    assert check_transparency(buf.getvalue()) is True


def test_invalid_image():
    with pytest.raises(WallpaperError):
        convert(b"nope", SIZE, MODE_NORMAL)


def test_device_filename():
    sha = "abcdef0123456789" * 4
    assert device_filename("Sea: view", sha, ".bmp") == "Sea_view-abcdef01.bmp"
    assert device_filename("...", sha, ".png") == "wallpaper-abcdef01.png"
