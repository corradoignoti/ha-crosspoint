"""Tests for EPUB metadata extraction."""

from __future__ import annotations

import io
import zipfile

import pytest
from PIL import Image

from custom_components.crosspoint.epub import (
    THUMBNAIL_SIZE,
    EpubError,
    make_thumbnail,
    read_epub,
)

from .epub_factory import make_epub


@pytest.mark.parametrize("style", ["epub3", "epub2"])
def test_metadata_and_cover(tmp_path, style):
    meta = read_epub(str(make_epub(tmp_path / "a.epub", cover=style)))
    assert meta.title == "Dune"
    assert meta.authors == ("Frank Herbert",)
    assert meta.cover.startswith(b"\x89PNG")


def test_no_cover_and_no_title(tmp_path):
    meta = read_epub(str(make_epub(tmp_path / "a.epub", title=None, cover=None)))
    assert meta.title is None
    assert meta.cover is None


def test_multiple_authors(tmp_path):
    path = make_epub(tmp_path / "a.epub", authors=("A. One", "B. Two"))
    assert read_epub(str(path)).authors == ("A. One", "B. Two")


def test_not_an_epub(tmp_path):
    path = tmp_path / "bad.epub"
    path.write_bytes(b"not a zip")
    with pytest.raises(EpubError):
        read_epub(str(path))


def test_entities_rejected(tmp_path):
    path = tmp_path / "a.epub"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><x/>',
        )
    with pytest.raises(EpubError):
        read_epub(str(path))


def test_thumbnail():
    image = io.BytesIO()
    Image.new("RGB", (1200, 1800), "blue").save(image, "PNG")
    thumb = make_thumbnail(image.getvalue())
    with Image.open(io.BytesIO(thumb)) as img:
        assert img.format == "JPEG"
        assert img.width <= THUMBNAIL_SIZE[0]
        assert img.height <= THUMBNAIL_SIZE[1]
    assert make_thumbnail(b"garbage") is None
