"""Helpers shared by the EPUB transformations applied before sending a book."""

from __future__ import annotations

import html
import io
import posixpath
import re
import zipfile
from collections.abc import Iterable
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
XHTML_TYPES = {"application/xhtml+xml", "text/html"}
XHTML_EXTENSIONS = {".xhtml", ".html", ".htm", ".xht"}

TAG_RE = re.compile(r"<(item|itemref)\b[^>]*?(?:/>|>\s*</\1\s*>|>)", re.S)
ATTR_RE = re.compile(r"([\w:.-]+)\s*=\s*([\"'])(.*?)\2", re.S)


class SkipError(Exception):
    """The book, or one of its files, cannot be transformed safely."""


def opf_path(archive: zipfile.ZipFile) -> str:
    """Return the archive path of the package document."""
    root = ET.fromstring(archive.read("META-INF/container.xml"))
    rootfile = root.find(f".//{{{CONTAINER_NS}}}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise SkipError("no package document")
    return rootfile.get("full-path", "")


def attrs(tag: str) -> dict[str, str]:
    """Return the attributes of a tag (unescaped values)."""
    return {m.group(1): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def resolve(base_dir: str, href: str) -> str:
    """Resolve a (percent-encoded, relative) href to an archive path."""
    return posixpath.normpath(posixpath.join(base_dir, unquote(href)))


def manifest(opf: str, opf_dir: str) -> dict[str, dict[str, str]]:
    """Return the manifest items keyed by archive path (in ``path``)."""
    items: dict[str, dict[str, str]] = {}
    for match in TAG_RE.finditer(opf):
        if match.group(1) != "item":
            continue
        item = attrs(match.group(0))
        href = item.get("href")
        if not href or not item.get("id"):
            continue
        item["path"] = resolve(opf_dir, href)
        items[item["path"]] = item
    return items


def spine(opf: str) -> Iterable[tuple[str, str]]:
    """Yield (idref, properties) of the spine items in reading order."""
    for match in TAG_RE.finditer(opf):
        if match.group(1) == "itemref":
            item = attrs(match.group(0))
            if item.get("idref"):
                yield item["idref"], item.get("properties", "")


def relative(path: str, base_dir: str) -> str:
    """Return a percent-encoded href to ``path`` from ``base_dir``."""
    return quote(posixpath.relpath(path, base_dir or "."), safe="/")


def unique(name: str, taken: set[str | None]) -> str:
    """Return ``name``, or ``name-N``, not present in ``taken``."""
    candidate, n = name, 1
    while candidate in taken:
        n += 1
        candidate = f"{name}-{n}"
    return candidate


def write_archive(
    archive: zipfile.ZipFile,
    changed: dict[str, bytes],
    removed: frozenset[str] | set[str] = frozenset(),
) -> bytes:
    """Write a copy of ``archive`` with changed, added and removed entries.

    The mimetype entry comes first and is stored uncompressed, as the OCF
    specification requires.
    """
    changed = dict(changed)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        dst.writestr(
            zipfile.ZipInfo("mimetype"), b"application/epub+zip", zipfile.ZIP_STORED
        )
        written = {"mimetype"}
        for info in archive.infolist():
            if info.filename in written or info.filename in removed:
                continue
            data = changed.pop(info.filename, None)
            if data is None:
                data = archive.read(info)
            dst.writestr(info, data, info.compress_type)
            written.add(info.filename)
        for name, data in changed.items():
            if name not in removed:
                dst.writestr(name, data, zipfile.ZIP_DEFLATED)
    return out.getvalue()
