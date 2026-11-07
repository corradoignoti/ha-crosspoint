"""Optimize an EPUB for the e-ink screen before sending it.

This mirrors the "Optimize EPUB" step of the CrossPoint firmware file manager
(``src/network/html/js/epub-optimizer.js``) and of jtvargas/crosspoint-app:

- raster images are converted to grayscale on a white background, scaled
  down to fit the screen and stored as baseline JPEG; references in XHTML,
  CSS, OPF and NCX follow the new ``.jpg`` names, and stale ``width`` and
  ``height`` of ``<img>`` elements are dropped;
- SVG elements that only wrap a raster image become a plain ``<img>``;
- embedded fonts are removed, with their ``@font-face`` rules and their
  obfuscation entries in ``META-INF/encryption.xml``: the firmware renders
  with its own fonts and never loads them;
- a defensive stylesheet is added to every XHTML document, a missing
  ``<meta name="cover">`` is added to the package, and the NCX identifier is
  aligned with the package identifier.

Like the split, it works on a copy: the library file is never changed. Books
with encrypted content other than fonts (DRM) are left untouched, and the
result is used only when it is smaller than the original.
"""

from __future__ import annotations

import html
import io
import logging
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from PIL import Image, ImageOps

from .epub_package import (
    TAG_RE,
    XHTML_EXTENSIONS,
    SkipError,
    attrs,
    manifest,
    opf_path,
    relative,
    resolve,
    write_archive,
)

_LOGGER = logging.getLogger(__name__)

# Bump when the output changes, so cached copies are rebuilt.
OPTIMIZER_VERSION = 1

# Limits from crosspoint-app (EPUBOptimizerConfig).
_MAX_EPUB_BYTES = 150 * 1024 * 1024
_MAX_ENTRIES = 2_000
_MAX_ENTRY_BYTES = 64 * 1024 * 1024
_MAX_MEGAPIXELS = 50
_JPEG_QUALITY = 85
_SKIP_OPTIMAL_JPEG_BYTES = 200 * 1024
_MIN_PROCESS_DIMENSION = 200

_RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2", ".eot"}
_FONT_TYPE_RE = re.compile(
    r"^(font/|application/font-|application/x-font-|"
    r"application/vnd\.ms-(opentype|fontobject)$)",
    re.I,
)
_ENC_NS = "http://www.w3.org/2001/04/xmlenc#"

DEFENSIVE_STYLE = (
    '<style type="text/css">img,svg{max-width:100%;height:auto}'
    "body{overflow-wrap:break-word}table{max-width:100%;table-layout:fixed}"
    "pre,code{white-space:pre-wrap;word-wrap:break-word}"
    "*{box-sizing:border-box}</style>"
)

_LINK_RE = re.compile(r"(\b(?:xlink:)?(?:href|src)\s*=\s*)([\"'])(.*?)\2", re.S | re.I)
_CSS_URL_RE = re.compile(r"\burl\(\s*(?:([\"'])(.*?)\1|([^'\")\s]+))\s*\)", re.S)
_FONT_FACE_RE = re.compile(r"@font-face\s*\{[^{}]*\}\s*", re.I)
_IMG_TAG_RE = re.compile(r"<img\b(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>", re.I)
_DIMENSION_RE = re.compile(
    r"\s+(?:width|height)\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>/]+)", re.I
)
_STYLE_ATTR_RE = re.compile(r"(\sstyle\s*=\s*)([\"'])(.*?)\2", re.S | re.I)
_DIMENSION_DECL_RE = re.compile(r"(?:^|;)\s*(?:width|height)\s*:[^;]*", re.I)
_SVG_RE = re.compile(r"<(?:svg:)?svg\b.*?</(?:svg:)?svg\s*>", re.S | re.I)
_SVG_IMAGE_RE = re.compile(
    r"<(?:svg:)?image\b(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>", re.S | re.I
)
_HEAD_END_RE = re.compile(r"</(?:\w+:)?head\s*>", re.I)
_ITEM_TAG_RE = re.compile(r"[ \t]*<item\b[^>]*?(?:/>|>\s*</item\s*>)[ \t]*\n?", re.S)
_META_COVER_RE = re.compile(r"<(?:\w+:)?meta\b[^>]*\bname\s*=\s*[\"']cover[\"']", re.I)
_METADATA_END_RE = re.compile(r"</((?:\w+:)?)metadata\s*>", re.I)
_UNIQUE_ID_RE = re.compile(
    r"<(?:\w+:)?package\b[^>]*\bunique-identifier\s*=\s*[\"']([^\"']+)[\"']"
)
_IDENTIFIER_RE = re.compile(
    r"<(?:\w+:)?identifier\b([^>]*)>([^<]*)</(?:\w+:)?identifier\s*>", re.I
)
_NCX_UID_RE = re.compile(
    r"(<meta\b[^>]*\bname\s*=\s*[\"']dtb:uid[\"'][^>]*\bcontent\s*=\s*)([\"'])(.*?)\2",
    re.S,
)


@dataclass(slots=True)
class _Plan:
    """What changes in the archive."""

    renamed: dict[str, str] = field(default_factory=dict)  # old path -> new path
    changed: dict[str, bytes] = field(default_factory=dict)
    removed: set[str] = field(default_factory=set)
    fonts: set[str] = field(default_factory=set)


def optimize_epub(data: bytes, screen: tuple[int, int] = (480, 800)) -> bytes | None:
    """Return the EPUB optimized for a screen of (width, height), or None."""
    try:
        return _optimize(data, screen)
    except (SkipError, zipfile.BadZipFile, ET.ParseError, KeyError) as err:
        _LOGGER.debug("EPUB optimization skipped: %s", err)
    except (OSError, ValueError, UnicodeError, RuntimeError) as err:
        _LOGGER.debug("EPUB optimization failed: %s", err)
    return None


def _ext(path: str) -> str:
    return posixpath.splitext(path)[1].lower()


def _optimize(data: bytes, screen: tuple[int, int]) -> bytes | None:
    if len(data) > _MAX_EPUB_BYTES:
        raise SkipError("book too large")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        if len(infos) > _MAX_ENTRIES:
            raise SkipError("too many entries")
        if any(i.file_size > _MAX_ENTRY_BYTES for i in infos):
            raise SkipError("entry too large")
        names = {i.filename for i in infos}
        package = opf_path(archive)
        opf = archive.read(package).decode("utf-8")
        opf_dir = posixpath.dirname(package)
        items = manifest(opf, opf_dir)

        plan = _Plan()
        plan.fonts = {n for n in names if _ext(n) in _FONT_EXTENSIONS} | {
            path
            for path, item in items.items()
            if _FONT_TYPE_RE.match(item.get("media-type", "")) and path in names
        }
        if "META-INF/encryption.xml" in names:
            _check_encryption(archive.read("META-INF/encryption.xml"), plan.fonts)
            plan.removed.add("META-INF/encryption.xml")
        plan.removed |= plan.fonts

        images = sorted(n for n in names if _ext(n) in _RASTER_EXTENSIONS)
        texts = sorted(
            n
            for n in names
            if _ext(n) in XHTML_EXTENSIONS | {".css", ".ncx"} and n not in plan.removed
        )
        has_svg = any(
            _ext(n) in XHTML_EXTENSIONS and b"<svg" in archive.read(n).lower()
            for n in texts
        )
        if not images and not plan.fonts and not has_svg:
            return None  # text-only book: nothing to gain

        for path in images:
            converted = _convert_image(archive.read(path), screen)
            if converted is None:
                continue
            target = path
            if _ext(path) not in {".jpg", ".jpeg"}:
                target = posixpath.splitext(path)[0] + ".jpg"
                n = 1
                while target in names or target in plan.changed:
                    n += 1
                    target = f"{posixpath.splitext(path)[0]}-{n}.jpg"
                plan.renamed[path] = target
                plan.removed.add(path)
            plan.changed[target] = converted

        for path in texts:
            raw = archive.read(path)
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            new = _rewrite_text(text, path, plan)
            if new != text:
                plan.changed[path] = new.encode("utf-8")

        new_opf = _rewrite_opf(opf, package, items, plan)
        identifier = _package_identifier(new_opf)
        for path in texts:
            if _ext(path) == ".ncx" and identifier:
                text = plan.changed.get(path, archive.read(path)).decode("utf-8-sig")
                synced = _NCX_UID_RE.sub(
                    lambda m: (
                        f"{m.group(1)}{m.group(2)}{html.escape(identifier)}{m.group(2)}"
                    ),
                    text,
                )
                if synced != text:
                    plan.changed[path] = synced.encode("utf-8")
        if new_opf != opf:
            plan.changed[package] = new_opf.encode("utf-8")
        if not plan.changed and not plan.removed:
            return None
        result = write_archive(archive, plan.changed, plan.removed)

    if len(result) >= len(data):
        _LOGGER.debug("EPUB optimization not smaller, keeping the original")
        return None
    _LOGGER.debug(
        "EPUB optimized: %d -> %d bytes (%d images, %d fonts)",
        len(data),
        len(result),
        sum(1 for p in plan.changed if _ext(p) in {".jpg", ".jpeg"}),
        len(plan.fonts),
    )
    return result


def _check_encryption(xml: bytes, fonts: set[str]) -> None:
    """Refuse books whose encryption.xml covers anything but fonts (DRM)."""
    root = ET.fromstring(xml)
    for reference in root.iter(f"{{{_ENC_NS}}}CipherReference"):
        uri = unquote(reference.get("URI", ""))
        if posixpath.normpath(uri) not in fonts:
            raise SkipError("encrypted content")


# --- Images -----------------------------------------------------------------


def _convert_image(data: bytes, screen: tuple[int, int]) -> bytes | None:
    """Return the image as a grayscale baseline JPEG, or None to keep it."""
    try:
        with Image.open(io.BytesIO(data)) as source:
            width, height = source.size
            if width <= 0 or height <= 0:
                return None
            if width * height > _MAX_MEGAPIXELS * 1_000_000:
                return None  # decompression bomb guard: never decoded
            fmt = source.format
            max_w, max_h = screen
            fits = width <= max_w and height <= max_h
            if fmt == "JPEG" and fits and len(data) <= _SKIP_OPTIMAL_JPEG_BYTES:
                return None
            tiny = width < _MIN_PROCESS_DIMENSION and height < _MIN_PROCESS_DIMENSION
            if tiny and fmt in {"JPEG", "PNG"}:
                return None  # ornaments and separators
            source.seek(0)
            image = ImageOps.exif_transpose(source)
            image = _on_white(image)
            if not tiny:
                image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.save(
                out, "JPEG", quality=_JPEG_QUALITY, optimize=True, progressive=False
            )
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None
    result = out.getvalue()
    if fmt == "JPEG" and len(result) >= len(data):
        return None
    return result


def _on_white(image: Image.Image) -> Image.Image:
    """Return the image in grayscale, with transparency blended on white."""
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode in {"RGBA", "LA", "PA"}:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        image = background
    return image.convert("L")


# --- Text -------------------------------------------------------------------


def _new_reference(value: str, base: str, plan: _Plan) -> str | None:
    """Return the reference updated for a renamed image, or None."""
    if not plan.renamed or "://" in value or value.startswith(("data:", "#", "/")):
        return None
    cut = len(value)
    for sep in "#?":
        if sep in value:
            cut = min(cut, value.index(sep))
    target = plan.renamed.get(resolve(base, value[:cut]))
    if target is None:
        return None
    return relative(target, base) + value[cut:]


def _rewrite_css(css: str, base: str, plan: _Plan) -> str:
    css = _FONT_FACE_RE.sub("", css) if plan.fonts else css

    def url(match: re.Match[str]) -> str:
        value = match.group(2) if match.group(1) else match.group(3)
        new = _new_reference(value, base, plan)
        if new is None:
            return match.group(0)
        return f'url("{new}")'

    return _CSS_URL_RE.sub(url, css)


def _rewrite_text(text: str, path: str, plan: _Plan) -> str:
    base = posixpath.dirname(path)
    if _ext(path) == ".css":
        return _rewrite_css(text, base, plan)

    is_xhtml = _ext(path) in XHTML_EXTENSIONS
    if is_xhtml:
        # Strip stale sizes first, so the <img> replacing an SVG keeps its
        # intentional height:auto.
        text = _IMG_TAG_RE.sub(_strip_dimensions, text)
        text = _SVG_RE.sub(_unwrap_svg, text)

    def link(match: re.Match[str]) -> str:
        new = _new_reference(html.unescape(match.group(3)), base, plan)
        if new is None:
            return match.group(0)
        return f"{match.group(1)}{match.group(2)}{html.escape(new)}{match.group(2)}"

    text = _LINK_RE.sub(link, text)
    if is_xhtml:
        if "url(" in text or (plan.fonts and "@font-face" in text):
            text = _rewrite_css(text, base, plan)
        if DEFENSIVE_STYLE not in text:
            text = _HEAD_END_RE.sub(
                lambda m: DEFENSIVE_STYLE + m.group(0), text, count=1
            )
    return text


def _unwrap_svg(match: re.Match[str]) -> str:
    """Replace an SVG that only wraps a raster image by an <img>."""
    block = match.group(0)
    for image in _SVG_IMAGE_RE.finditer(block):
        tag = attrs(image.group(0))
        href = tag.get("xlink:href") or tag.get("href") or ""
        path = href.split("#", 1)[0].split("?", 1)[0]
        if _ext(unquote(path)) in _RASTER_EXTENSIONS:
            return (
                '<img style="max-width:100%;height:auto" '
                f'src="{html.escape(href)}" alt=""/>'
            )
    return block  # a real vector drawing


def _strip_dimensions(match: re.Match[str]) -> str:
    """Drop width and height of an <img>: the image size may have changed."""
    tag = _DIMENSION_RE.sub("", match.group(0))

    def style(m: re.Match[str]) -> str:
        value = _DIMENSION_DECL_RE.sub("", m.group(3)).strip().strip(";").strip()
        return f"{m.group(1)}{m.group(2)}{value}{m.group(2)}" if value else ""

    return _STYLE_ATTR_RE.sub(style, tag)


# --- Package document ---------------------------------------------------------


def _rewrite_opf(
    opf: str, package: str, items: dict[str, dict[str, str]], plan: _Plan
) -> str:
    opf_dir = posixpath.dirname(package)

    def item(match: re.Match[str]) -> str:
        tag = match.group(0)
        if match.group(1) != "item":
            return tag
        info = attrs(tag)
        path = resolve(opf_dir, info.get("href", ""))
        if path in plan.fonts:
            return ""
        if path in plan.renamed or (
            path in plan.changed and info.get("media-type", "").startswith("image/")
        ):
            tag = _set_attr(tag, "media-type", "image/jpeg")
        if path in plan.renamed:
            tag = _set_attr(tag, "href", relative(plan.renamed[path], opf_dir))
        props = info.get("properties", "").split()
        if "svg" in props:
            content = plan.changed.get(path)
            if content is not None and b"<svg" not in content.lower():
                props.remove("svg")
                tag = _set_attr(tag, "properties", " ".join(props) or None)
        return tag

    opf = TAG_RE.sub(item, opf)
    # Font items were replaced by empty strings: drop the blank lines left.
    opf = re.sub(r"\n[ \t]*\n", "\n", opf) if plan.fonts else opf
    return _ensure_cover_meta(opf, items, plan)


def _set_attr(tag: str, name: str, value: str | None) -> str:
    pattern = re.compile(rf"\s{re.escape(name)}\s*=\s*([\"']).*?\1", re.S)
    if value is None:
        return pattern.sub("", tag)
    new = f' {name}="{html.escape(value)}"'
    if pattern.search(tag):
        return pattern.sub(lambda _: new, tag, count=1)
    end = tag.rindex("/>") if tag.rstrip().endswith("/>") else tag.rindex(">")
    return tag[:end].rstrip() + new + tag[end:]


def _ensure_cover_meta(opf: str, items: dict[str, dict[str, str]], plan: _Plan) -> str:
    """Add <meta name="cover"> (EPUB 2 readers rely on it) when missing."""
    if _META_COVER_RE.search(opf):
        return opf
    images = [
        i
        for p, i in items.items()
        if i.get("media-type", "").startswith("image/") and p not in plan.fonts
    ]
    cover = next(
        (i for i in images if "cover-image" in i.get("properties", "").split()), None
    ) or next(
        (
            i
            for i in images
            if "cover" in i["id"].lower() or "cover" in i.get("href", "").lower()
        ),
        None,
    )
    match = _METADATA_END_RE.search(opf)
    if cover is None or match is None:
        return opf
    meta = f'<{match.group(1)}meta name="cover" content="{html.escape(cover["id"])}"/>'
    return opf[: match.start()] + meta + opf[match.start() :]


def _package_identifier(opf: str) -> str | None:
    unique_id = _UNIQUE_ID_RE.search(opf)
    identifiers = list(_IDENTIFIER_RE.finditer(opf))
    for match in identifiers:
        if unique_id and attrs(match.group(1)).get("id") == unique_id.group(1):
            return html.unescape(match.group(2).strip())
    return html.unescape(identifiers[0].group(2).strip()) if identifiers else None
