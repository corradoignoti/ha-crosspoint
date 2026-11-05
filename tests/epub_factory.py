"""Build small EPUB files for tests."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from PIL import Image

CONTAINER = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""


def png(color: str = "red", size=(600, 900)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, "PNG")
    return out.getvalue()


def make_epub(
    path: Path,
    *,
    title: str | None = "Dune",
    authors: tuple[str, ...] = ("Frank Herbert",),
    cover: str | None = "epub3",
    extra: str = "",
) -> Path:
    """Write an EPUB with an EPUB 3 or EPUB 2 style cover, or none."""
    meta = []
    if title:
        meta.append(f"<dc:title>{title}</dc:title>")
    meta += [f"<dc:creator>{a}</dc:creator>" for a in authors]
    items = ['<item id="text" href="text.xhtml" media-type="application/xhtml+xml"/>']
    if cover == "epub3":
        items.append(
            '<item id="img" href="images/cover%20art.png" '
            'media-type="image/png" properties="cover-image"/>'
        )
    elif cover == "epub2":
        meta.append('<meta name="cover" content="img"/>')
        items.append(
            '<item id="img" href="images/cover%20art.png" media-type="image/png"/>'
        )
    opf = f"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">{"".join(meta)}{extra}</metadata>
  <manifest>{"".join(items)}</manifest>
</package>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", CONTAINER)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/text.xhtml", "<html/>")
        if cover:
            archive.writestr("OEBPS/images/cover art.png", png())
    return path
