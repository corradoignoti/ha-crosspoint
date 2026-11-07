"""Split long chapters of an EPUB into smaller files before sending it.

The CrossPoint firmware works on one spine item at a time: it inflates the
whole XHTML file to the SD card and lays out every page of it before the
first page is shown, and repeats the layout whenever the reading settings
change. A book whose text sits in one or a few huge files (common with
Project Gutenberg and quick conversions) therefore makes the reader wait for
a long time. Splitting such files into parts of a bounded size keeps every
wait short.

The split works on a copy of the EPUB; the library file is never changed:

- only XHTML spine items whose visible text exceeds the threshold are split;
- the cut points are the top-level headings (h1-h3) when there are at least
  two, merging small adjacent sections; a section still above the threshold,
  or a file without headings, is cut at block boundaries by text size;
- the first part keeps the original file name, so links and table of
  contents entries without a fragment keep working; the other parts are new
  manifest items placed right after it in the spine;
- links (XHTML, NCX, nav, OPF guide) whose fragment now lives in another part
  are rewritten to point to it;
- books with encrypted resources (DRM, obfuscated fonts) or a fixed layout
  are left untouched, and so is every file that fails to parse.
"""

from __future__ import annotations

import copy
import html
import html.entities
import io
import itertools
import logging
import posixpath
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

_LOGGER = logging.getLogger(__name__)

DEFAULT_SPLIT_THRESHOLD = 15_000  # characters of visible text, as crosspoint-app

_XHTML_NS = "http://www.w3.org/1999/xhtml"
_XML_NS = "http://www.w3.org/XML/1998/namespace"
_CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
_XHTML_TYPES = {"application/xhtml+xml", "text/html"}
_LINKED_TYPES = _XHTML_TYPES | {"application/x-dtbncx+xml"}
# Refuse to process archives larger than this once inflated.
_MAX_TOTAL_BYTES = 256 * 1024 * 1024

_HEADINGS = {"h1", "h2", "h3"}
_WRAPPERS = {"div", "section", "article", "main"}
_MEDIA = {"img", "image", "svg", "video", "audio", "object"}
_VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}  # fmt: skip

_TAG_RE = re.compile(r"<(item|itemref)\b[^>]*?(?:/>|>\s*</\1\s*>|>)", re.S)
_ATTR_RE = re.compile(r"([\w:.-]+)\s*=\s*([\"'])(.*?)\2", re.S)
_LINK_RE = re.compile(r"(\b(?:xlink:)?(?:href|src)\s*=\s*)([\"'])(.*?)\2", re.S)
_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]*);")
_XML_DECL_RE = re.compile(r"^\s*<\?xml[^>]*\?>", re.S)
_DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>\[]*(?:\[[^\]]*\])?\s*>", re.I | re.S)
_ENCODING_RE = re.compile(rb"^\s*<\?xml[^>]*encoding\s*=\s*[\"']([\w.-]+)[\"']")
_FIXED_LAYOUT_RE = re.compile(r"rendition:layout[^<]*pre-paginated")


class _SkipError(Exception):
    """The book or one of its files cannot be split safely."""


@dataclass(slots=True)
class _Split:
    """A spine item split into parts."""

    path: str  # archive path of the original file (keeps part 1)
    parts: list[str] = field(default_factory=list)  # archive paths, part 1 first
    ids: dict[str, str] = field(default_factory=dict)  # fragment -> archive path


def split_epub(data: bytes, threshold: int = DEFAULT_SPLIT_THRESHOLD) -> bytes | None:
    """Return the EPUB with its long chapters split, or None if unchanged."""
    try:
        return _split_epub(data, threshold)
    except (_SkipError, zipfile.BadZipFile, ET.ParseError, KeyError) as err:
        _LOGGER.debug("Chapter split skipped: %s", err)
    except (OSError, ValueError, UnicodeError, RuntimeError) as err:
        _LOGGER.debug("Chapter split failed: %s", err)
    return None


def _split_epub(data: bytes, threshold: int) -> bytes | None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if sum(i.file_size for i in infos) > _MAX_TOTAL_BYTES:
            raise _SkipError("archive too large")
        names = {i.filename for i in infos}
        if "META-INF/encryption.xml" in names:
            raise _SkipError("encrypted resources")
        opf_path = _opf_path(archive.read("META-INF/container.xml"))
        opf = archive.read(opf_path).decode("utf-8")
        if _FIXED_LAYOUT_RE.search(opf):
            raise _SkipError("fixed layout")
        opf_dir = posixpath.dirname(opf_path)
        items = _manifest(opf, opf_dir)

        changed: dict[str, bytes] = {}
        splits: list[_Split] = []
        new_items: dict[str, list[tuple[str, str]]] = {}  # item id -> (id, href)
        taken = set(names)
        by_id = {attrs["id"]: attrs for attrs in items.values()}
        used_ids: set[str | None] = set(by_id)
        for idref, props in _spine(opf):
            item = by_id.get(idref)
            if (
                item is None
                or item.get("media-type") not in _XHTML_TYPES
                or "nav" in item.get("properties", "").split()
                or "pre-paginated" in props
                or item["path"] not in names
                or any(s.path == item["path"] for s in splits)
            ):
                continue
            try:
                result = _split_document(
                    archive.read(item["path"]), item["path"], threshold, taken
                )
            except (_SkipError, ET.ParseError, UnicodeError, ValueError) as err:
                _LOGGER.debug("Not splitting %s: %s", item["path"], err)
                continue
            if result is None:
                continue
            split, contents = result
            splits.append(split)
            changed.update(contents)
            taken.update(split.parts)
            entries = []
            for number, part in enumerate(split.parts[1:], start=2):
                part_id = _unique(f"{idref}-part{number}", used_ids)
                used_ids.add(part_id)
                entries.append((part_id, _relative(part, opf_dir)))
            new_items[idref] = entries

        if not splits:
            return None

        changed[opf_path] = _update_opf(opf, items, new_items).encode("utf-8")
        linked = {
            a["path"] for a in items.values() if a.get("media-type") in _LINKED_TYPES
        }
        linked |= {p for s in splits for p in s.parts}
        linked.add(opf_path)
        _rewrite_links(
            archive, sorted(linked & (names | set(changed))), splits, changed
        )
        _LOGGER.debug(
            "Split %d chapter(s) into %d files",
            len(splits),
            sum(len(s.parts) for s in splits),
        )
        return _write_archive(archive, infos, changed)


def _opf_path(container: bytes) -> str:
    root = ET.fromstring(container)
    rootfile = root.find(f".//{{{_CONTAINER_NS}}}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise _SkipError("no package document")
    return rootfile.get("full-path", "")


def _attrs(tag: str) -> dict[str, str]:
    return {m.group(1): html.unescape(m.group(3)) for m in _ATTR_RE.finditer(tag)}


def _manifest(opf: str, opf_dir: str) -> dict[str, dict[str, str]]:
    """Return the manifest items keyed by archive path."""
    items: dict[str, dict[str, str]] = {}
    for match in _TAG_RE.finditer(opf):
        if match.group(1) != "item":
            continue
        attrs = _attrs(match.group(0))
        href = attrs.get("href")
        if not href or not attrs.get("id"):
            continue
        attrs["path"] = posixpath.normpath(posixpath.join(opf_dir, unquote(href)))
        items[attrs["path"]] = attrs
    return items


def _spine(opf: str) -> Iterable[tuple[str, str]]:
    """Yield (idref, properties) of the spine items in reading order."""
    for match in _TAG_RE.finditer(opf):
        if match.group(1) == "itemref":
            attrs = _attrs(match.group(0))
            if attrs.get("idref"):
                yield attrs["idref"], attrs.get("properties", "")


def _update_opf(
    opf: str,
    items: dict[str, dict[str, str]],
    new_items: dict[str, list[tuple[str, str]]],
) -> str:
    """Add the new parts to the manifest and to the spine, after part 1."""
    by_id = {a["id"]: a for a in items.values()}

    def insert(match: re.Match[str]) -> str:
        tag = match.group(0)
        attrs = _attrs(tag)
        if match.group(1) == "item":
            idref = attrs.get("id", "")
            if idref not in new_items:
                return tag
            media = by_id[idref]["media-type"]
            props = by_id[idref].get("properties", "")
            extra = f' properties="{html.escape(props)}"' if props else ""
            return tag + "".join(
                f'\n    <item id="{html.escape(part_id)}" '
                f'href="{html.escape(href)}" media-type="{media}"{extra}/>'
                for part_id, href in new_items[idref]
            )
        idref = attrs.get("idref", "")
        if idref not in new_items:
            return tag
        linear = attrs.get("linear")
        extra = f' linear="{html.escape(linear)}"' if linear else ""
        return tag + "".join(
            f'\n    <itemref idref="{html.escape(part_id)}"{extra}/>'
            for part_id, _ in new_items[idref]
        )

    return _TAG_RE.sub(insert, opf)


def _relative(path: str, base_dir: str) -> str:
    return quote(posixpath.relpath(path, base_dir or "."), safe="/")


def _unique(name: str, taken: set[str | None]) -> str:
    candidate, n = name, 1
    while candidate in taken:
        n += 1
        candidate = f"{name}-{n}"
    return candidate


# --- XHTML documents --------------------------------------------------------


def _decode(raw: bytes) -> str:
    match = _ENCODING_RE.match(raw)
    return raw.decode(match.group(1).decode("ascii") if match else "utf-8")


def _xml_entities(text: str) -> str:
    """Replace HTML named entities, unknown to a plain XML parser, by numbers."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in {"amp", "lt", "gt", "quot", "apos"}:
            return match.group(0)
        char = html.entities.html5.get(name + ";")
        if char is None:
            raise _SkipError(f"unknown entity &{name};")
        return "".join(f"&#{ord(c)};" for c in char)

    return _ENTITY_RE.sub(repl, text)


def _namespaces(text: str) -> dict[str, str]:
    """Return the prefixes declared in a document, as {uri: prefix}."""
    found: dict[str, str] = {}
    for _event, (prefix, uri) in ET.iterparse(io.StringIO(text), events=("start-ns",)):
        found.setdefault(uri, prefix)
    return found


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def _text_len(element: ET.Element) -> int:
    return len("".join(element.itertext()).strip()) + len((element.tail or "").strip())


def _is_heading(element: ET.Element) -> bool:
    if _local(element.tag) in _HEADINGS:
        return True
    if _local(element.tag) in _WRAPPERS and not (element.text or "").strip():
        first = next(iter(element), None)
        return first is not None and _local(first.tag) in _HEADINGS
    return False


# A unit is a block placed in a part, with the wrappers it sits in.
_Unit = tuple[tuple[ET.Element, ...], ET.Element]


def _units(body: ET.Element, threshold: int) -> list[_Unit]:
    """Return the blocks of the body, in order, that the parts are made of.

    Books often wrap a chapter (or the whole file) in div or section
    elements, sometimes nested: a wrapper longer than the threshold is
    opened and its children become blocks, so the split can happen inside.
    """
    units: list[_Unit] = []

    def expand(parent: ET.Element, ancestors: tuple[ET.Element, ...]) -> None:
        for child in parent:
            if (
                _local(child.tag) in _WRAPPERS
                and _text_len(child) > threshold
                and not (child.text or "").strip()
                and not (child.tail or "").strip()
                and not any((c.tail or "").strip() for c in child)
            ):
                expand(child, (*ancestors, child))
            else:
                units.append((ancestors, child))

    expand(body, (body,))
    return units


def _segments(children: list[ET.Element], threshold: int) -> list[tuple[int, int]]:
    """Return the [start, end) ranges of children forming each part."""
    sizes = [_text_len(c) for c in children]
    prefix = [0]
    for size in sizes:
        prefix.append(prefix[-1] + size)

    def total(a: int, b: int) -> int:
        return prefix[b] - prefix[a]

    starts = [i for i, child in enumerate(children) if _is_heading(child)]
    if len(starts) >= 2:
        bounds = sorted({0, *starts, len(children)})
        sections = list(itertools.pairwise(bounds))
    else:
        sections = [(0, len(children))]

    merged: list[tuple[int, int]] = []
    for a, b in sections:
        # Merge small adjacent sections; a short preamble always joins the
        # next section instead of becoming a part of its own.
        if merged and (
            total(merged[-1][0], b) <= threshold or total(*merged[-1]) < threshold // 4
        ):
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))

    result: list[tuple[int, int]] = []
    for a, b in merged:
        start, size = a, 0
        for i in range(a, b - 1):
            size += sizes[i]
            if (
                size >= threshold
                and total(i + 1, b) >= threshold // 4
                and not _is_heading(children[i])
            ):
                result.append((start, i + 1))
                start, size = i + 1, 0
        result.append((start, b))
    return result


def _split_document(
    raw: bytes, path: str, threshold: int, taken: set[str]
) -> tuple[_Split, dict[str, bytes]] | None:
    text = _decode(raw)
    doctype = _DOCTYPE_RE.search(text[:2048])
    text = _xml_entities(_XML_DECL_RE.sub("", text, count=1))
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    root = ET.fromstring(text, parser=parser)
    body = root.find(f"{{{_XHTML_NS}}}body")
    if body is None:
        raise _SkipError("no XHTML body")
    if _text_len(body) <= threshold:
        return None
    units = _units(body, threshold)
    segments = _segments([element for _, element in units], threshold)
    if len(segments) < 2:
        return None

    namespaces = _namespaces(text)
    prolog = '<?xml version="1.0" encoding="utf-8"?>\n'
    if doctype:
        prolog += doctype.group(0) + "\n"
    stem, ext = posixpath.splitext(path)
    split = _Split(path=path, parts=[path])
    for number in range(2, len(segments) + 1):
        part = f"{stem}_part{number}{ext}"
        while part in taken or part in split.parts:
            part = f"{posixpath.splitext(part)[0]}_{number}{ext}"
        split.parts.append(part)

    contents: dict[str, bytes] = {}
    kept_ids: set[int] = set()  # wrappers whose id was already written
    for (start, end), part in zip(segments, split.parts, strict=True):
        part_root = _part_tree(root, body, units[start:end], kept_ids)
        if part != path:
            for element in part_root.iter():
                for key in ("id", f"{{{_XML_NS}}}id"):
                    if element.get(key):
                        split.ids.setdefault(element.get(key, ""), part)
                if _local(element.tag) == "a" and element.get("name"):
                    split.ids.setdefault(element.get("name", ""), part)
        contents[part] = (prolog + _serialize(part_root, namespaces)).encode("utf-8")
    return split, contents


def _part_tree(
    root: ET.Element,
    body: ET.Element,
    units: list[_Unit],
    kept_ids: set[int],
) -> ET.Element:
    """Build a document with the head of ``root`` and the given blocks.

    The wrappers around the blocks are recreated in every part; a wrapper
    keeps its id only in the first part it appears in.
    """
    new_root = ET.Element(root.tag, dict(root.attrib))
    new_root.text = root.text
    stack: list[tuple[ET.Element, ET.Element]] = []  # (original, copy)

    def clone(original: ET.Element, parent: ET.Element) -> ET.Element:
        attrs = dict(original.attrib)
        if id(original) in kept_ids:
            attrs.pop("id", None)
            attrs.pop(f"{{{_XML_NS}}}id", None)
        kept_ids.add(id(original))
        element = ET.SubElement(parent, original.tag, attrs)
        element.tail = original.tail
        return element

    for child in root:
        if child is body:
            first = id(body) not in kept_ids
            new_body = clone(body, new_root)
            if first:
                new_body.text = body.text  # text before the first block
            stack = [(body, new_body)]
            for ancestors, element in units:
                depth = 0
                while (
                    depth < len(stack)
                    and depth < len(ancestors)
                    and stack[depth][0] is ancestors[depth]
                ):
                    depth += 1
                del stack[depth:]
                for original in ancestors[depth:]:
                    stack.append((original, clone(original, stack[-1][1])))
                stack[-1][1].append(element)
        elif isinstance(child.tag, str):
            new_root.append(copy.deepcopy(child))
    return new_root


def _serialize(root: ET.Element, namespaces: dict[str, str]) -> str:
    """Serialize a tree keeping the prefixes the source document used.

    ElementTree would rename prefixes (``epub:type`` to ``ns0:type``), which
    breaks readers that match attribute names literally.
    """
    prefixes = dict(namespaces)
    prefixes.setdefault(_XHTML_NS, "")
    prefixes[_XML_NS] = "xml"
    used = set(prefixes.values())

    def qname(name: str) -> str:
        if not name.startswith("{"):
            return name
        uri, local = name[1:].split("}", 1)
        if uri not in prefixes:
            prefixes[uri] = _unique("ns", used)  # type: ignore[arg-type]
            used.add(prefixes[uri])
        prefix = prefixes[uri]
        return f"{prefix}:{local}" if prefix else local

    out: list[str] = []

    def write(element: ET.Element, top: bool) -> None:
        if element.tag is ET.Comment:
            out.append(f"<!--{element.text or ''}-->")
        elif element.tag is ET.ProcessingInstruction:
            out.append(f"<?{element.text or ''}?>")
        else:
            tag = qname(element.tag)
            attrs = "".join(
                f' {qname(k)}="{_escape_attr(v)}"' for k, v in element.attrib.items()
            )
            if top:
                # Collect every namespace first so the declarations are complete.
                for el in element.iter():
                    if isinstance(el.tag, str):
                        qname(el.tag)
                        for k in el.attrib:
                            qname(k)
                attrs = (
                    "".join(
                        f' xmlns{":" + p if p else ""}="{_escape_attr(u)}"'
                        for u, p in prefixes.items()
                        if p != "xml"
                    )
                    + attrs
                )
            out.append(f"<{tag}{attrs}")
            if (
                element.text is None
                and len(element) == 0
                and _local(element.tag) in _VOID
            ):
                out.append("/>")
            else:
                out.append(">")
                out.append(_escape_text(element.text or ""))
                for child in element:
                    write(child, False)
                out.append(f"</{tag}>")
        out.append(_escape_text(element.tail or ""))

    write(root, True)
    return "".join(out)


def _escape_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    return (
        _escape_text(text)
        .replace('"', "&quot;")
        .replace("\n", "&#10;")
        .replace("\t", "&#9;")
    )


# --- Links and archive ------------------------------------------------------


def _rewrite_links(
    archive: zipfile.ZipFile,
    paths: list[str],
    splits: list[_Split],
    changed: dict[str, bytes],
) -> None:
    """Point links to fragments that moved to another part at that part."""
    by_path = {s.path: s for s in splits}
    origin = {part: s.path for s in splits for part in s.parts}

    for path in paths:
        raw = changed.get(path)
        if raw is None:
            raw = archive.read(path)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        base = posixpath.dirname(path)

        def repl(match: re.Match[str], path: str = path, base: str = base) -> str:
            value = html.unescape(match.group(3))
            if "#" not in value or "://" in value or value.startswith("mailto:"):
                return match.group(0)
            target, fragment = value.split("#", 1)
            if target:
                resolved = posixpath.normpath(posixpath.join(base, unquote(target)))
            else:
                resolved = origin.get(path, path)
            split = by_path.get(resolved)
            if split is None:
                return match.group(0)
            dest = split.ids.get(unquote(fragment), split.path)
            current = path if not target else resolved
            if dest == current:
                return match.group(0)
            new = (
                f"#{fragment}"
                if dest == path
                else f"{_relative(dest, base)}#{fragment}"
            )
            quote_char = match.group(2)
            return f"{match.group(1)}{quote_char}{html.escape(new)}{quote_char}"

        new_text = _LINK_RE.sub(repl, text)
        if new_text != text:
            changed[path] = new_text.encode("utf-8")


def _write_archive(
    archive: zipfile.ZipFile, infos: list[zipfile.ZipInfo], changed: dict[str, bytes]
) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        # The mimetype entry must come first and be stored uncompressed.
        dst.writestr(
            zipfile.ZipInfo("mimetype"), b"application/epub+zip", zipfile.ZIP_STORED
        )
        written = {"mimetype"}
        for info in infos:
            if info.filename in written:
                continue
            data = changed.pop(info.filename, None)
            if data is None:
                data = archive.read(info)
            dst.writestr(info, data, info.compress_type)
            written.add(info.filename)
        for name, data in changed.items():
            dst.writestr(name, data, zipfile.ZIP_DEFLATED)
    return out.getvalue()
