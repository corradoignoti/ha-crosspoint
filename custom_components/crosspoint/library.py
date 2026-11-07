"""Library of books and wallpapers found in the shared folder."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import timedelta
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    CONF_SCAN_INTERVAL,
    CONF_WALLPAPERS_DIR,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    KIND_BOOK,
    KIND_WALLPAPER,
)
from .epub import EpubError, make_thumbnail, read_epub
from .store import Transfer, TransferStore, sha256_file

if TYPE_CHECKING:
    from . import CrossPointConfigEntry

_LOGGER = logging.getLogger(__name__)

BOOK_EXTENSIONS = (".epub",)
WALLPAPER_EXTENSIONS = (".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp")
CACHE_VERSION = 1
# Bump to discard cached entries when indexing changes (v2: wallpaper thumbnails).
CACHE_FORMAT = 2

STATUS_NOT_INSTALLED = "not_installed"
STATUS_INSTALLED = "installed"
STATUS_MODIFIED = "modified"
STATUS_MISSING = "missing_from_library"


@dataclass(frozen=True, slots=True)
class LibraryFile:
    """A file found in the library folder, with cached metadata."""

    kind: str
    file: str  # path relative to the kind's subfolder, POSIX separators
    size: int
    mtime_ns: int
    sha256: str
    title: str | None = None
    authors: tuple[str, ...] = ()
    has_cover: bool = False


@dataclass(frozen=True, slots=True)
class LibraryData:
    """Result of one library scan."""

    books: dict[str, LibraryFile]
    wallpapers: dict[str, LibraryFile]


@dataclass(frozen=True, slots=True)
class LibraryItem:
    """A library file (or a tracked transfer) with its install status."""

    kind: str
    file: str
    status: str
    entry: LibraryFile | None
    transfer: Transfer | None

    def as_dict(self) -> dict[str, Any]:
        """Serialize for the WebSocket API."""
        data: dict[str, Any] = {"kind": self.kind, "file": self.file}
        data["status"] = self.status
        if self.entry:
            data.update(
                size=self.entry.size,
                sha256=self.entry.sha256,
                title=self.entry.title,
                authors=list(self.entry.authors),
                has_cover=self.entry.has_cover,
            )
        if self.transfer:
            data.update(
                sent_at=self.transfer.sent_at,
                device_path=self.transfer.device_path,
            )
        return data


def _status(entry: LibraryFile | None, transfer: Transfer | None) -> str:
    if entry is None:
        return STATUS_MISSING
    if transfer is None:
        return STATUS_NOT_INSTALLED
    return STATUS_INSTALLED if transfer.sha256 == entry.sha256 else STATUS_MODIFIED


class LibraryCoordinator(DataUpdateCoordinator[LibraryData]):
    """Scan the shared library folder periodically and on demand.

    Hashes and EPUB metadata are cached by (path, size, mtime), so a rescan
    only reads new or changed files. Cover thumbnails are kept in the Home
    Assistant cache directory, named by the book hash.
    """

    config_entry: CrossPointConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CrossPointConfigEntry,
        transfers: TransferStore,
    ) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} library",
            update_interval=timedelta(minutes=minutes),
        )
        root = Path(entry.data[CONF_LIBRARY_PATH])
        self._roots = {
            KIND_BOOK: root / entry.data[CONF_BOOKS_DIR],
            KIND_WALLPAPER: root / entry.data[CONF_WALLPAPERS_DIR],
        }
        self.covers_dir = Path(hass.config.cache_path(DOMAIN, entry.entry_id, "covers"))
        # Books prepared for sending (optimized, split), named by the book hash.
        self.prepared_dir = Path(
            hass.config.cache_path(DOMAIN, entry.entry_id, "prepared")
        )
        self._transfers = transfers
        self._cache_store: Store[dict[str, Any]] = Store(
            hass, CACHE_VERSION, f"{DOMAIN}.{entry.entry_id}.library"
        )
        self._cache: dict[str, LibraryFile] | None = None
        # Install status depends on the transfers too.
        entry.async_on_unload(transfers.async_add_listener(self.async_update_listeners))

    def root(self, kind: str) -> Path:
        """Return the library subfolder for a kind of file."""
        return self._roots[kind]

    async def _async_update_data(self) -> LibraryData:
        if self._cache is None:
            stored = await self._cache_store.async_load() or {}
            self._cache = {}
            if stored.get("format") != CACHE_FORMAT:
                stored = {}
            for raw in stored.get("files", []):
                item = LibraryFile(**{**raw, "authors": tuple(raw.get("authors", ()))})
                self._cache[f"{item.kind}:{item.file}"] = item
        data, cache = await self.hass.async_add_executor_job(
            self._scan, dict(self._cache)
        )
        if cache != self._cache:
            self._cache = cache
            await self._cache_store.async_save(
                {
                    "format": CACHE_FORMAT,
                    "files": [asdict(f) for f in cache.values()],
                }
            )
        return data

    def _scan(
        self, cache: dict[str, LibraryFile]
    ) -> tuple[LibraryData, dict[str, LibraryFile]]:
        """Walk the library folders (blocking; runs in the executor)."""
        found: dict[str, dict[str, LibraryFile]] = {KIND_BOOK: {}, KIND_WALLPAPER: {}}
        new_cache: dict[str, LibraryFile] = {}
        extensions = {KIND_BOOK: BOOK_EXTENSIONS, KIND_WALLPAPER: WALLPAPER_EXTENSIONS}
        for kind, root in self._roots.items():
            if not root.is_dir():
                _LOGGER.warning("Library folder %s does not exist", root)
                continue
            for path in sorted(root.rglob("*")):
                if (
                    not path.is_file()
                    or path.name.startswith(".")
                    or path.suffix.lower() not in extensions[kind]
                ):
                    continue
                rel = path.relative_to(root).as_posix()
                key = f"{kind}:{rel}"
                try:
                    stat = path.stat()
                    cached = cache.get(key)
                    if (
                        cached
                        and cached.size == stat.st_size
                        and cached.mtime_ns == stat.st_mtime_ns
                        and (not cached.has_cover or self._cover_path(cached).exists())
                    ):
                        item = cached
                    else:
                        item = self._index(kind, rel, path, stat)
                except OSError as err:
                    _LOGGER.warning("Cannot read %s: %s", path, err)
                    continue
                found[kind][rel] = item
                new_cache[key] = item
        self._prune_covers(new_cache)
        self._prune_prepared(new_cache)
        return (
            LibraryData(books=found[KIND_BOOK], wallpapers=found[KIND_WALLPAPER]),
            new_cache,
        )

    def _index(
        self, kind: str, rel: str, path: Path, stat: os.stat_result
    ) -> LibraryFile:
        sha256 = sha256_file(path)
        title: str | None = None
        authors: tuple[str, ...] = ()
        has_cover = False
        if kind == KIND_BOOK:
            try:
                meta = read_epub(str(path))
            except EpubError as err:
                _LOGGER.warning("Cannot read EPUB metadata of %s: %s", path, err)
            else:
                title, authors = meta.title, meta.authors
                if meta.cover:
                    has_cover = self._write_thumbnail(sha256, meta.cover)
        else:
            has_cover = self._write_thumbnail(sha256, path.read_bytes())
        return LibraryFile(
            kind=kind,
            file=rel,
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            sha256=sha256,
            title=title or (path.stem if kind == KIND_BOOK else None),
            authors=authors,
            has_cover=has_cover,
        )

    def _write_thumbnail(self, sha256: str, image: bytes) -> bool:
        if (thumb := make_thumbnail(image)) is None:
            return False
        self.covers_dir.mkdir(parents=True, exist_ok=True)
        (self.covers_dir / f"{sha256}.jpg").write_bytes(thumb)
        return True

    def _cover_path(self, item: LibraryFile) -> Path:
        return self.covers_dir / f"{item.sha256}.jpg"

    def _prune_covers(self, cache: dict[str, LibraryFile]) -> None:
        if not self.covers_dir.is_dir():
            return
        keep = {f"{f.sha256}.jpg" for f in cache.values() if f.has_cover}
        for cover in self.covers_dir.glob("*.jpg"):
            if cover.name not in keep:
                cover.unlink(missing_ok=True)

    def _prune_prepared(self, cache: dict[str, LibraryFile]) -> None:
        if not self.prepared_dir.is_dir():
            return
        keep = {f.sha256 for f in cache.values()}
        for prepared in self.prepared_dir.glob("*.epub"):
            if prepared.name.split("-", 1)[0] not in keep:
                prepared.unlink(missing_ok=True)

    def cover_path(self, sha256: str) -> Path | None:
        """Return the thumbnail of a library file, if there is one."""
        if self.data is None:
            return None
        for item in (*self.data.books.values(), *self.data.wallpapers.values()):
            if item.sha256 == sha256 and item.has_cover:
                return self._cover_path(item)
        return None

    def items(self, kind: str) -> list[LibraryItem]:
        """Return library files and tracked transfers of a kind, with status."""
        files = (
            {}
            if self.data is None
            else (self.data.books if kind == KIND_BOOK else self.data.wallpapers)
        )
        transfers = {t.file: t for t in self._transfers.all(kind)}
        return [
            LibraryItem(
                kind=kind,
                file=name,
                status=_status(files.get(name), transfers.get(name)),
                entry=files.get(name),
                transfer=transfers.get(name),
            )
            for name in sorted(files.keys() | transfers.keys(), key=str.casefold)
        ]


async def async_remove_library_cache(hass: HomeAssistant, entry_id: str) -> None:
    """Delete cached metadata and covers of a removed config entry."""
    await Store(hass, CACHE_VERSION, f"{DOMAIN}.{entry_id}.library").async_remove()
    await hass.async_add_executor_job(
        partial(shutil.rmtree, hass.config.cache_path(DOMAIN, entry_id), True)
    )
