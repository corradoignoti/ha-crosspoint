"""Read title, authors and cover from EPUB files (blocking helpers)."""

from __future__ import annotations

import io
import posixpath
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from urllib.parse import unquote

from PIL import Image

_NS = {
    "c": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}
_MAX_XML_BYTES = 4 * 1024 * 1024
_MAX_COVER_BYTES = 20 * 1024 * 1024
_IMAGE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")
THUMBNAIL_SIZE = (300, 450)


class EpubError(Exception):
    """The file is not a readable EPUB."""


@dataclass(frozen=True, slots=True)
class EpubMetadata:
    """Metadata extracted from an EPUB package document."""

    title: str | None
    authors: tuple[str, ...]
    cover: bytes | None  # raw image bytes as stored in the EPUB


def _read_limited(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as err:
        raise EpubError(f"Missing {name}") from err
    if info.file_size > limit:
        raise EpubError(f"{name} is too large")
    return archive.read(info)


def _parse_xml(data: bytes) -> ET.Element:
    if b"<!ENTITY" in data:  # no entity expansion tricks in package files
        raise EpubError("XML entities are not allowed")
    try:
        return ET.fromstring(data)
    except ET.ParseError as err:
        raise EpubError(f"Invalid XML: {err}") from err


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    return " ".join(element.text.split()) or None


def _find_cover_href(package: ET.Element) -> str | None:
    manifest = package.find("opf:manifest", _NS)
    if manifest is None:
        return None
    items = manifest.findall("opf:item", _NS)

    # EPUB 3: <item properties="cover-image">
    for item in items:
        if "cover-image" in (item.get("properties") or "").split():
            return item.get("href")

    # EPUB 2: <meta name="cover" content="<item id>">
    for meta in package.findall("opf:metadata/opf:meta", _NS):
        if meta.get("name") == "cover" and (cover_id := meta.get("content")):
            for item in items:
                if item.get("id") == cover_id:
                    return item.get("href")

    # Fallback: an image whose id or file name mentions "cover".
    for item in items:
        if (
            item.get("media-type") in _IMAGE_TYPES
            and "cover" in ((item.get("id") or "") + (item.get("href") or "")).lower()
        ):
            return item.get("href")
    return None


def read_epub(path: str) -> EpubMetadata:
    """Return the metadata of an EPUB file."""
    try:
        with zipfile.ZipFile(path) as archive:
            container = _parse_xml(
                _read_limited(archive, "META-INF/container.xml", _MAX_XML_BYTES)
            )
            rootfile = container.find("c:rootfiles/c:rootfile", _NS)
            opf_path = rootfile.get("full-path") if rootfile is not None else None
            if not opf_path:
                raise EpubError("No package document")
            package = _parse_xml(_read_limited(archive, opf_path, _MAX_XML_BYTES))

            metadata = package.find("opf:metadata", _NS)
            title = (
                _text(metadata.find("dc:title", _NS)) if metadata is not None else None
            )
            authors = tuple(
                name
                for creator in (
                    metadata.findall("dc:creator", _NS) if metadata is not None else []
                )
                if (name := _text(creator))
            )

            cover = None
            if href := _find_cover_href(package):
                cover_path = posixpath.normpath(
                    posixpath.join(posixpath.dirname(opf_path), unquote(href))
                )
                try:
                    cover = _read_limited(archive, cover_path, _MAX_COVER_BYTES)
                except EpubError:
                    cover = None
    except (zipfile.BadZipFile, OSError) as err:
        raise EpubError(str(err)) from err
    return EpubMetadata(title=title, authors=authors, cover=cover)


def make_thumbnail(image: bytes) -> bytes | None:
    """Return a JPEG thumbnail of an image, or None if it cannot be decoded.

    Transparent areas are shown on white.
    """
    try:
        with Image.open(io.BytesIO(image)) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            rgba = img.convert("RGBA")
            flat = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            flat.alpha_composite(rgba)
            out = io.BytesIO()
            flat.convert("RGB").save(out, "JPEG", quality=80, optimize=True)
            return out.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
