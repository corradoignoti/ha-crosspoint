"""Tests of the chapter split applied to books before sending them."""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree as ET

from custom_components.crosspoint.epub_split import split_epub

from .epub_factory import CONTAINER

XHTML = "http://www.w3.org/1999/xhtml"
PARA = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10  # ~570 chars


def chapter(body: str, *, title: str = "Book") -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!DOCTYPE html>\n"
        f'<html xmlns="{XHTML}" xmlns:epub="http://www.idpf.org/2007/ops">'
        f'<head><title>{title}</title><link rel="stylesheet" href="style.css"/></head>'
        f"<body>{body}</body></html>"
    )


def paragraphs(count: int, prefix: str = "p") -> str:
    return "".join(f'<p id="{prefix}{i}">{PARA}&nbsp;{i}</p>' for i in range(count))


def make_book(
    files: dict[str, str],
    *,
    extra_files: dict[str, str] | None = None,
    metadata: str = "",
) -> bytes:
    manifest = "".join(
        f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>'
        for i, name in enumerate(files)
    )
    manifest += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(files)))
    opf = (
        '<?xml version="1.0"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>Book</dc:title>{metadata}</metadata>"
        f'<manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>'
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", CONTAINER)
        archive.writestr("OEBPS/content.opf", opf)
        for name, text in files.items():
            archive.writestr(f"OEBPS/{name}", text)
        for name, text in (extra_files or {}).items():
            archive.writestr(name, text)
    return out.getvalue()


def ncx(*targets: str) -> str:
    points = "".join(
        f'<navPoint id="n{i}" playOrder="{i + 1}"><navLabel><text>{i}</text>'
        f'</navLabel><content src="{src}"/></navPoint>'
        for i, src in enumerate(targets)
    )
    return (
        '<?xml version="1.0"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f"<navMap>{points}</navMap></ncx>"
    )


def read(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {i.filename: archive.read(i) for i in archive.infolist()}


def spine(files: dict[str, bytes]) -> list[str]:
    opf = files["OEBPS/content.opf"].decode()
    hrefs = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
    return [hrefs[i] for i in re.findall(r'<itemref idref="([^"]+)"', opf)]


def body_text(raw: bytes) -> str:
    root = ET.fromstring(raw)
    return "".join(root.find(f"{{{XHTML}}}body").itertext())


def test_short_book_is_unchanged():
    data = make_book({"a.xhtml": chapter(paragraphs(5))})
    assert split_epub(data) is None


def test_not_an_epub_is_unchanged():
    assert split_epub(b"not a zip") is None


def test_split_at_headings_keeps_order_and_text():
    sections = "".join(
        f"<h2 id='h{n}'>Chapter {n}</h2>{paragraphs(20, f's{n}p')}" for n in range(3)
    )
    original = chapter(sections)
    data = make_book({"a.xhtml": original, "b.xhtml": chapter("<p>end</p>")})
    files = read(split_epub(data))

    order = spine(files)
    assert order == ["a.xhtml", "a_part2.xhtml", "a_part3.xhtml", "b.xhtml"]
    # Each part starts with its heading and keeps head and stylesheet.
    for n, name in enumerate(order[:3]):
        raw = files[f"OEBPS/{name}"]
        assert raw.startswith(
            b'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>'
        )
        root = ET.fromstring(raw)
        first = root.find(f"{{{XHTML}}}body")[0]
        assert first.get("id") == f"h{n}"
        assert root.find(f".//{{{XHTML}}}link").get("href") == "style.css"
        assert b"xmlns:epub=" in raw
    joined = "".join(body_text(files[f"OEBPS/{n}"]) for n in order[:3])
    assert joined.replace("\xa0", " ") == body_text(
        original.replace("&nbsp;", "&#160;").encode()
    ).replace("\xa0", " ")
    # mimetype first and stored.
    with zipfile.ZipFile(io.BytesIO(split_epub(data))) as archive:
        first = archive.infolist()[0]
        assert first.filename == "mimetype"
        assert first.compress_type == zipfile.ZIP_STORED


def test_small_sections_are_merged():
    sections = "".join(f"<h2>Poem {n}</h2>{paragraphs(2, f's{n}p')}" for n in range(40))
    files = read(split_epub(make_book({"a.xhtml": chapter(sections)})))
    parts = spine(files)
    assert 2 <= len(parts) < 10
    for name in parts:
        assert len(body_text(files[f"OEBPS/{name}"])) <= 15_000


def test_split_without_headings_by_size():
    data = make_book({"a.xhtml": chapter(f"<div class='ch'>{paragraphs(100)}</div>")})
    files = read(split_epub(data))
    parts = spine(files)
    assert len(parts) == 4
    for name in parts:
        raw = files[f"OEBPS/{name}"]
        # The wrapper div is kept in every part.
        assert b'<div class="ch">' in raw
        assert len(body_text(raw)) < 20_000


def test_links_and_toc_follow_moved_fragments():
    sections = "".join(
        f"<h2 id='h{n}'>Chapter {n}</h2>{paragraphs(30, f's{n}p')}" for n in range(2)
    )
    sections = '<p><a href="#h1">jump</a></p>' + sections
    data = make_book(
        {
            "text/a.xhtml": chapter(sections),
            "text/notes.xhtml": chapter('<p><a href="a.xhtml#s1p3">back</a></p>'),
        },
        extra_files={"OEBPS/toc.ncx": ncx("text/a.xhtml", "text/a.xhtml#h1")},
    )
    files = read(split_epub(data))
    assert spine(files)[:2] == ["text/a.xhtml", "text/a_part2.xhtml"]
    assert b'href="a_part2.xhtml#h1"' in files["OEBPS/text/a.xhtml"]
    assert b'href="a_part2.xhtml#s1p3"' in files["OEBPS/text/notes.xhtml"]
    toc = files["OEBPS/toc.ncx"]
    assert b'src="text/a.xhtml"' in toc
    assert b'src="text/a_part2.xhtml#h1"' in toc


def test_threshold_is_configurable():
    data = make_book({"a.xhtml": chapter(paragraphs(40))})
    assert split_epub(data) is not None
    assert split_epub(data, threshold=100_000) is None


def test_split_is_idempotent():
    data = make_book({"a.xhtml": chapter(paragraphs(100))})
    assert split_epub(split_epub(data)) is None


def test_encrypted_book_is_unchanged():
    data = make_book(
        {"a.xhtml": chapter(paragraphs(100))},
        extra_files={"META-INF/encryption.xml": "<encryption/>"},
    )
    assert split_epub(data) is None


def test_fixed_layout_book_is_unchanged():
    data = make_book(
        {"a.xhtml": chapter(paragraphs(100))},
        metadata='<meta property="rendition:layout">pre-paginated</meta>',
    )
    assert split_epub(data) is None


def test_malformed_chapter_is_left_alone():
    data = make_book(
        {
            "a.xhtml": chapter(paragraphs(100)) + "<broken",
            "b.xhtml": chapter(paragraphs(100, "q")),
        }
    )
    files = read(split_epub(data))
    assert spine(files)[0] == "a.xhtml"
    assert spine(files)[1] == "b.xhtml"
    assert files["OEBPS/a.xhtml"].endswith(b"<broken")


def test_nested_wrappers_next_to_empty_elements():
    # Like Project Gutenberg: body > div > div (chapter), plus an empty marker.
    inner = f"<div id='chap'><h2>Chapter</h2>{paragraphs(60)}</div>"
    data = make_book(
        {"a.xhtml": chapter(f"<div class='book'>{inner}</div><div id='end'/>")}
    )
    files = read(split_epub(data))
    parts = spine(files)
    assert len(parts) >= 2
    for name in parts:
        assert len(body_text(files[f"OEBPS/{name}"])) <= 20_000
    # Wrapper ids appear once; the empty marker stays at the end of the text.
    joined = b"".join(files[f"OEBPS/{name}"] for name in parts)
    assert joined.count(b'id="chap"') == 1
    assert files[f"OEBPS/{parts[-1]}"].count(b'id="end"') == 1
