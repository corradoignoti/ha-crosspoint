# Implementation plan

This plan turns the specification in [CLAUDE.md](../CLAUDE.md) into phases. Each
phase ends with passing tests and lint, and every change lands as an atomic
commit (one topic per commit).

## Status

| Phase | Topic                         | Status      |
|-------|-------------------------------|-------------|
| 0     | Scaffolding                   | Done        |
| 1     | Device client + config flow   | Done        |
| 2     | Device reachability           | Done        |
| 3     | Library scan                  | Done        |
| 4     | Tracking store + book actions | Done        |
| 5     | Wallpapers                    | Done        |
| 6     | Sidebar panel (frontend)      | Not started |
| 7     | Reading stats                 | Not started |
| 8     | Services, i18n, docs, release | Not started |

Recommended order: 0, 1, 2, 4 (with one test book end to end), then 3, 5, 6, 7, 8.

## Verified facts

These close the "To verify" items in the specification.

### CrossPoint firmware web server

Source: `docs/webserver-endpoints.md` in `crosspoint-reader/crosspoint-reader`.

HTTP, port 80, no authentication:

| Method | Path          | Parameters                                                        | Notes |
|--------|---------------|-------------------------------------------------------------------|-------|
| GET    | `/api/status` | none                                                              | JSON: `version`, `firmwareFamily`, `ip`, `mode`, `rssi`, `freeHeap`, `uptime`, `device`. Used as the reachability probe. |
| GET    | `/api/files`  | query `path` (default `/`)                                        | JSON array of `{name, size, isDirectory, isEpub}`. Dotfiles are hidden unless `showHiddenFiles` is enabled. |
| GET    | `/download`   | query `path`                                                      | File bytes. |
| POST   | `/upload`     | query `path`, `overwrite` (`1`/`true`); multipart field `file`    | Without `overwrite`, an existing name returns `400`. |
| POST   | `/mkdir`      | form `name`, `path`                                               | |
| POST   | `/delete`     | form `path`, or `paths` (JSON array string)                       | Non-empty folders are rejected. |
| POST   | `/rename`, `/move` | form                                                         | Files only. Not used yet. |

WebSocket upload, port 81 (`ws://<host>:81/`):

1. Client sends text `START:<filename>:<size>:<path>`.
2. Server replies `READY`.
3. Client sends binary chunks.
4. Server sends `PROGRESS:<received>:<total>` every 64 KB and at completion.
5. Server sends `DONE`, or `ERROR:<message>`.

WebSocket uploads never overwrite, and only one upload runs at a time.
Incomplete uploads are deleted by the firmware.

UDP discovery, port 8134: send `hello`, the reply is
`crosspoint (on <hostname>);<ws_port>`.

### Sleep screen folders

Source: `USER_GUIDE.md` in `crosspoint-reader/crosspoint-reader`.

- Normal sleep images: `/.sleep/` (fallback `/sleep/`), uncompressed 24-bit BMP
  recommended. A root `sleep.bmp` takes priority over both folders. The firmware
  picks one image at random when several are present.
- Transparent overlays (sleep mode "Transparent" or "Cover + Transparent"):
  `/.sleep-overlay/` (fallback `/sleep-overlay/`). PNG with alpha channel, or
  32-bit BGRA BMP. Opaque white pixels erase the content behind them.

### CrossPoint Sync API

Source: `docs/API.md` in `crosspoint-reader/crosspoint-sync`.

- Auth headers: `x-auth-user` and `x-auth-key` (lowercase hex MD5 of the
  password). Failures return `401` with `{"code": 2001}`; repeated failures may
  return `429`.
- `GET /users/auth` returns `{"authorized": "OK"}` and validates credentials.
- `GET /api/v1/stats/summary` returns `sessions`, `seconds`, `pages`,
  `completed`, `tod[4]` (seconds per time of day), `dow[7]` (seconds Mon–Sun),
  `anchor_day` (days since 2000-01-01), `history_b64` (reading-day bitmap),
  `streak`, `current_streak`, `devices[]` (`device_id`, `device`, `updated_at`).
- `GET /api/v1/stats/global` (optional `device_id`, `since`) returns
  `devices[]` with a per-device `stats` snapshot, plus `until` for
  incremental fetches.

## Repository layout

```
custom_components/crosspoint/
  __init__.py          # entry setup: runtime data, panel, WS API, services, card
  manifest.json
  const.py             # models and resolutions, ports, config keys, defaults
  config_flow.py       # discovery, device, library steps; options; reconfigure
  discovery.py         # UDP broadcast discovery
  api/errors.py        # CrossPointConnectionError, CrossPointResponseError
  api/device.py        # firmware web server client (HTTP + WebSocket upload)
  api/sync.py          # CrossPoint Sync stats client
  coordinator.py       # DeviceCoordinator, StatsCoordinator
  library.py           # folder scan, EPUB metadata and cover extraction
  store.py             # transfer tracking (helpers.storage.Store)
  wallpaper.py         # Pillow conversion pipeline
  binary_sensor.py     # device online
  sensor.py            # per-user reading stats
  services.py, services.yaml
  websocket_api.py     # commands used by the panel
  frontend/            # built panel and Lovelace card bundles
  strings.json, translations/
frontend_src/          # panel and card sources (built with esbuild/rollup)
tests/
```

## Phases

### Phase 0 — Scaffolding (done)

- `manifest.json`, `hacs.json`, `pyproject.toml` (ruff, pytest), README, MIT
  license.
- CI: hassfest, HACS validation, ruff and pytest
  (`pytest-homeassistant-custom-component`).
- All user-facing strings live in `strings.json` / `translations/` from the
  start (English and Italian), ready for later i18n.

### Phase 1 — Device client and config flow (done)

- `CrossPointDeviceClient`: status, file listing, `mkdir`, `ensure_dir`,
  `delete`, `upload`.
  - Upload prefers the WebSocket protocol and reports progress. It falls back
    to HTTP when the WebSocket server cannot be reached, and uses HTTP with
    `overwrite=1` when replacing a file.
  - An internal lock serializes uploads, matching the firmware limit.
  - File names containing `/` or `:` are rejected, since they would break the
    WebSocket `START` message.
- UDP discovery collects replies for about 2 seconds.
- Config flow:
  1. Discovered devices are offered for selection, with manual entry as an
     alternative.
  2. Address and model. The model is pre-filled from `/api/status` when it
     can be recognized. An unreachable device is accepted after a second
     submit, since the reader is usually not in File Transfer mode while
     configuring.
  3. Library folder: must be allowed by Home Assistant
     (`allowlist_external_dirs`, `/media`) and exist. The subfolders are
     created when missing.
- Options flow: library scan interval. Reconfigure flow: address, model and
  library folders.

### Phase 2 — Device reachability (done)

- `CrossPointDeviceCoordinator` polls `/api/status` every 20 seconds. Being
  offline is a normal state, not an update failure, so entities stay
  available.
- `binary_sensor.<device>_online` (device class `connectivity`) exposes the
  state. A diagnostic Wi-Fi signal sensor (RSSI, disabled by default) is
  available only while the device is online.
- The device registry entry carries the model and the firmware version, which
  is updated whenever the device reports a new one.
- `async_ensure_online()` probes the device immediately and raises the
  translated `device_offline` error. Every service and WebSocket command must
  call it first. `async_mark_connection_lost()` flips the state to offline
  when an operation loses the connection.

### Phase 3 — Library (done)

- `LibraryCoordinator` scans the books (`.epub`) and wallpapers (`.bmp`,
  `.gif`, `.jpeg`, `.jpg`, `.png`, `.webp`) subfolders recursively in the
  executor, at the options interval and on demand (`rescan_library`). Hidden
  files are skipped.
- SHA-256 and metadata are cached by `(path, size, mtime)` in Home Assistant
  storage, so a rescan only reads new or changed files.
- EPUB metadata (`epub.py`) uses `zipfile` and ElementTree:
  `META-INF/container.xml`, then the OPF for `dc:title`, `dc:creator` and the
  cover (`properties="cover-image"`, then `meta name="cover"`, then an image
  named like a cover). Package files are size-limited and entity declarations
  are rejected. The file name is the title fallback.
- Covers become JPEG thumbnails (max 300 × 450) in the Home Assistant cache
  directory, `.cache/crosspoint/<entry_id>/covers/<sha256>.jpg`. Unused
  thumbnails are pruned on each scan, and everything is deleted with the
  config entry.
- `CrossPointCoverView` serves thumbnails at
  `/api/crosspoint/<entry_id>/cover/<sha256>` (authentication required; the
  panel will use signed paths for image tags).
- Item status combines the scan and the transfer store: `not_installed`,
  `installed`, `modified` (hash differs from the sent one), or
  `missing_from_library` (tracked, but no longer in the folder). The store
  notifies the library on every change.
- Sensors: library books, and books on the device (with `modified` and
  `missing_from_library` counts as attributes).

### Phase 4 — Tracking store and book operations (done)

- `TransferStore` (Home Assistant storage, one file per config entry) records
  `{kind, file, sha256, size, sent_at, device_path}`, keyed by kind and
  library-relative path. Removing the config entry deletes it.
- `BookManager` serializes operations per entry:
  - `send_book`: validates the path (no escape from the books folder), checks
    the device is online, hashes the file, creates the destination folder,
    uploads, and records the transfer only after the device confirms.
    A tracked book is replaced automatically (HTTP overwrite); an untracked
    file with the same name on the device is refused unless `overwrite` is
    set. Returns `device_path` and `sha256` as the service response.
  - `remove_book`: only tracked books can be removed. The entry is forgotten
    only after the device confirms the deletion. If the device listing shows
    the file is already gone, the call fails unless `forget_missing` is set.
  - Connection failures mark the device offline right away.
- Destination folder on the device is an option, default `/Books`.
- Upload progress is published as `crosspoint_upload_progress` events
  (`entry_id`, `kind`, `file`, `received`, `total`), at most every 256 KB.
- Services take a `config_entry_id`, are registered in `async_setup`, and
  raise translated errors.

### Phase 5 — Wallpapers (done)

- Pipeline (`wallpaper.py`, Pillow): EXIF orientation, palette and grayscale
  transparency normalized to RGBA, `ImageOps.fit` to the model resolution
  (LANCZOS), grayscale, Floyd-Steinberg dithering to 4 evenly spaced gray
  levels (0, 85, 170, 255).
- Normal mode: alpha flattened on white, uncompressed 24-bit BMP sent to
  `/.sleep/`.
- Transparent mode: dithered gray in RGB plus the original alpha channel, PNG
  sent to `/.sleep-overlay/`. An image without transparent pixels is refused
  unless `force` is set; `WallpaperManager.async_check()` reports
  transparency without the device, for the panel warning.
- Device file names are `<safe stem>-<first 8 hex of source SHA-256>.<ext>`:
  sources with the same stem never collide, and a modified source gets a new
  file.
- One device copy per source image: re-sending the same conversion
  overwrites it in place; sending another mode (or a modified source) uploads
  the new file, then deletes the previous one.
- Transfers record the `mode`. Services `send_wallpaper` (`mode`, `force`;
  response `device_path`, `sha256`, `has_transparency`) and
  `remove_wallpaper`.
- Book and wallpaper operations share `TransferManager` (`transfers.py`):
  path validation, upload and delete with error mapping, progress events,
  removal of tracked files.

### Phase 6 — Sidebar panel

- Register a `panel_custom` with static files served through
  `async_register_static_paths`.
- Web component (Lit or vanilla), built from `frontend_src/` into a single
  committed bundle.
- Views:
  - Books: cover grid, status badges, Send / Remove / Re-send.
  - Wallpapers: thumbnails, mode choice, Send.
  - Header: device online state and Rescan button.
- Send and Remove are disabled while the device is offline; the panel follows
  the online entity state.
- WebSocket commands (admin only): `crosspoint/library`,
  `crosspoint/send_book`, `crosspoint/remove_book`,
  `crosspoint/send_wallpaper`, `crosspoint/wallpaper_check`,
  `crosspoint/rescan`.
- UI strings come from a translation dictionary, not inline literals.

### Phase 7 — Reading stats

- Sync users configured as config subentries (or an options list). Store the
  MD5 key, never the plain password, and never expose credentials to the
  frontend.
- Server URL configurable, default `https://sync.crosspointreader.com`.
- Validate credentials with `/users/auth`.
- One `StatsCoordinator` per user, polling every 15–30 minutes, plus the
  `refresh_reading_stats` service. Independent of device reachability.
- Sensors per user: total reading time, pages, books finished, sessions,
  current streak, longest streak, reading minutes today. `dow` and `tod` as
  attributes.
- Lovelace card `custom:crosspoint-stats-card`, registered with
  `add_extra_js_url`: single user or side-by-side comparison, reading the
  sensor entities.

### Phase 8 — Services, i18n, docs, release

- `services.yaml` with selectors for `send_book`, `remove_book`,
  `send_wallpaper` (mode `normal` / `transparent`), `rescan_library`,
  `refresh_reading_stats`.
- Complete Italian translations and the panel dictionary.
- README: HACS install, Samba setup, panel and card usage, security note.
- Tests: config flow, device client against the fake firmware server, EPUB
  parser, wallpaper pipeline (golden images), store, services.
- First tagged release for HACS.

## Open questions

- Encoding of `history_b64` and the element shape of `daily[]` in the Sync
  stats: needed for "reading minutes today". Requires a real sample or the
  server source.
- Deleting files inside dot-folders (`/.sleep`, `/.sleep-overlay`): to be
  tested on real firmware, since dotfiles are hidden from listings.
- Values of `/api/status` `device` for each model, to make model detection
  reliable.
- Default destination folder for books on the device (`/Books` assumed).
- Expected orientation of sleep images on the X3 (528 × 792 assumed portrait).
- Gray levels used by the firmware for sleep images (4 assumed). If the
  firmware renders them in 1 bit, dither to 2 levels instead.

## Estimate

About 10–13 working days in total, of which phases 0–5 (about 6 days) are
done.
