"""Tests of the EPUB optimization applied to books before sending them."""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

from PIL import Image

from custom_components.crosspoint.epub_optimize import DEFENSIVE_STYLE, optimize_epub
from custom_components.crosspoint.epub_split import split_epub

from .epub_factory import CONTAINER
from .test_epub_split import chapter, paragraphs

SCREEN = (480, 800)


def image(fmt: str, size: tuple[int, int], mode: str = "RGB") -> bytes:
    """Return a noisy image (realistic sizes); RGBA has a transparent border."""
    img = Image.effect_noise(size, 80).convert("RGB")
    if mode == "RGBA":
        alpha = Image.new("L", size, 0)
        alpha.paste(255, (size[0] // 4, size[1] // 4, size[0] // 2, size[1] // 2))
        img.putalpha(alpha)
    out = io.BytesIO()
    img.save(out, fmt)
    return out.getvalue()


ENCRYPTION = """<?xml version="1.0"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"
  xmlns:enc="http://www.w3.org/2001/04/xmlenc#">
  <enc:EncryptedData>
    <enc:EncryptionMethod Algorithm="http://www.idpf.org/2008/embedding"/>
    <enc:CipherData><enc:CipherReference URI="{uri}"/></enc:CipherData>
  </enc:EncryptedData>
</encryption>"""


def make_book(
    *,
    body: str = "",
    files: dict[str, bytes | str] | None = None,
    items: str = "",
    metadata: str = "",
    css: str = "",
    ncx_uid: str | None = None,
) -> bytes:
    manifest = (
        '<item id="c0" href="text/a.xhtml" media-type="application/xhtml+xml"/>'
        '<item id="css" href="style.css" media-type="text/css"/>' + items
    )
    if ncx_uid is not None:
        manifest += (
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        )
    opf = (
        '<?xml version="1.0"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" '
        'unique-identifier="uid">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:title>Book</dc:title><dc:identifier id="uid">urn:uuid:1234</dc:identifier>'
        f"{metadata}</metadata>\n"
        f"<manifest>\n{manifest}\n</manifest>\n"
        '<spine><itemref idref="c0"/></spine></package>'
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/text/a.xhtml", chapter(body))
        archive.writestr("OEBPS/style.css", css or "p{margin:0}")
        if ncx_uid is not None:
            archive.writestr(
                "OEBPS/toc.ncx",
                '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><head>'
                f'<meta name="dtb:uid" content="{ncx_uid}"/></head><navMap/></ncx>',
            )
        for name, data in (files or {}).items():
            archive.writestr(name, data)
    return out.getvalue()


def read(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {i.filename: archive.read(i) for i in archive.infolist()}


def test_text_only_book_is_unchanged():
    assert optimize_epub(make_book(body=paragraphs(3)), SCREEN) is None


def test_not_an_epub_is_unchanged():
    assert optimize_epub(b"nope", SCREEN) is None


def test_images_become_grayscale_jpeg_fitting_the_screen():
    png = image("PNG", (1200, 1600), "RGBA")
    data = make_book(
        body='<p><img src="../images/pic.png" width="1200" height="1600" '
        'style="width:1200px;color:red"/></p>',
        files={"OEBPS/images/pic.png": png},
        items='<item id="pic" href="images/pic.png" media-type="image/png"/>',
        css='div{background:url("images/pic.png")}',
    )
    files = read(optimize_epub(data, SCREEN))

    assert "OEBPS/images/pic.png" not in files
    with Image.open(io.BytesIO(files["OEBPS/images/pic.jpg"])) as img:
        assert img.format == "JPEG"
        assert img.mode == "L"
        assert img.size == (480, 640)
        assert "progressive" not in img.info
        # Transparent areas land on white, not black.
        assert img.getpixel((5, 5)) > 250
    text = files["OEBPS/text/a.xhtml"].decode()
    assert 'src="../images/pic.jpg"' in text
    assert "width=" not in text and "height=" not in text
    assert 'style="color:red"' in text
    assert DEFENSIVE_STYLE in text
    assert text.count(DEFENSIVE_STYLE) == 1
    assert 'url("images/pic.jpg")' in files["OEBPS/style.css"].decode()
    opf = files["OEBPS/content.opf"].decode()
    assert 'href="images/pic.jpg" media-type="image/jpeg"' in opf
    with zipfile.ZipFile(io.BytesIO(optimize_epub(data, SCREEN))) as archive:
        first = archive.infolist()[0]
        assert (first.filename, first.compress_type) == ("mimetype", zipfile.ZIP_STORED)


def test_small_images_are_kept():
    tiny = image("PNG", (120, 40))
    small_jpeg = image("JPEG", (300, 300))
    big = image("PNG", (900, 900))
    data = make_book(
        body='<p><img src="../t.png"/><img src="../s.jpg"/><img src="../b.png"/></p>',
        files={"OEBPS/t.png": tiny, "OEBPS/s.jpg": small_jpeg, "OEBPS/b.png": big},
    )
    files = read(optimize_epub(data, SCREEN))
    assert files["OEBPS/t.png"] == tiny
    assert files["OEBPS/s.jpg"] == small_jpeg
    assert "OEBPS/b.jpg" in files


def test_large_jpeg_is_scaled_in_place():
    big = image("JPEG", (1600, 2400))
    data = make_book(
        body='<p><img src="../images/p.jpg"/></p>',
        files={"OEBPS/images/p.jpg": big},
        items='<item id="p" href="images/p.jpg" media-type="image/jpeg"/>',
    )
    files = read(optimize_epub(data, SCREEN))
    with Image.open(io.BytesIO(files["OEBPS/images/p.jpg"])) as img:
        assert img.size == (480, 720)
        assert img.mode == "L"


def test_svg_wrapped_cover_becomes_img():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 600 900">'
        '<image width="600" height="900" xlink:href="../cover.png"/></svg>'
    )
    vector = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>'
    data = make_book(
        body=f"<div>{svg}</div><p>{vector}</p>",
        files={"OEBPS/cover.png": image("PNG", (600, 900))},
        items='<item id="cover-img" href="cover.png" media-type="image/png"/>',
    )
    files = read(optimize_epub(data, SCREEN))
    text = files["OEBPS/text/a.xhtml"].decode()
    assert '<img style="max-width:100%;height:auto" src="../cover.jpg" alt=""/>' in text
    assert "<circle" in text  # true vector drawings are kept
    opf = files["OEBPS/content.opf"].decode()
    assert '<meta name="cover" content="cover-img"/>' in opf
    ET.fromstring(files["OEBPS/text/a.xhtml"])  # still well-formed


def test_fonts_are_removed_and_book_can_be_split():
    long_body = f"<h2>One</h2>{paragraphs(30)}<h2>Two</h2>{paragraphs(30, 'q')}"
    data = make_book(
        body=long_body,
        files={
            "OEBPS/fonts/serif.ttf": b"\0" * 50_000,
            "META-INF/encryption.xml": ENCRYPTION.format(uri="OEBPS/fonts/serif.ttf"),
        },
        items='<item id="font" href="fonts/serif.ttf" media-type="font/ttf"/>',
        css='@font-face { font-family: "S"; src: url(fonts/serif.ttf); }\np{margin:0}',
    )
    # With the obfuscated font, the split refuses the book.
    assert split_epub(data) is None
    optimized = optimize_epub(data, SCREEN)
    files = read(optimized)
    assert "OEBPS/fonts/serif.ttf" not in files
    assert "META-INF/encryption.xml" not in files
    assert "@font-face" not in files["OEBPS/style.css"].decode()
    assert "serif.ttf" not in files["OEBPS/content.opf"].decode()
    assert split_epub(optimized) is not None


def test_drm_book_is_unchanged():
    data = make_book(
        body='<p><img src="../b.png"/></p>',
        files={
            "OEBPS/b.png": image("PNG", (900, 900)),
            "META-INF/encryption.xml": ENCRYPTION.format(uri="OEBPS/text/a.xhtml"),
        },
    )
    assert optimize_epub(data, SCREEN) is None


def test_ncx_identifier_is_synced():
    data = make_book(
        body='<p><img src="../b.png"/></p>',
        files={"OEBPS/b.png": image("PNG", (900, 900))},
        ncx_uid="something-else",
    )
    files = read(optimize_epub(data, SCREEN))
    assert b'content="urn:uuid:1234"' in files["OEBPS/toc.ncx"]


def test_screen_size_follows_the_model():
    data = make_book(
        body='<p><img src="../b.png"/></p>',
        files={"OEBPS/b.png": image("PNG", (1056, 1584))},
    )
    files = read(optimize_epub(data, (528, 792)))
    with Image.open(io.BytesIO(files["OEBPS/b.jpg"])) as img:
        assert img.size == (528, 792)


def test_optimization_is_idempotent():
    data = make_book(
        body='<p><img src="../b.png"/></p>',
        files={"OEBPS/b.png": image("PNG", (900, 900))},
    )
    assert optimize_epub(optimize_epub(data, SCREEN), SCREEN) is None
