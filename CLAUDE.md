# CLAUDE.md — CrossPoint integration for Home Assistant

## Language rules

- This file is written in English.
- The user may write prompts in Italian. Regardless of the prompt language, all code, identifiers, code comments, docstrings, commit messages and technical documentation must be written in English.

## Goal

A custom Home Assistant integration, distributed through HACS, that manages a library of books and wallpapers and sends them over Wi-Fi to an e-reader running CrossPoint firmware, while tracking what has been installed on the device.

## Architecture

- Type: custom integration (custom\_components), installable from HACS.
- Self-contained: the integration registers its own sidebar panel in Home Assistant. Clicking the CrossPoint entry opens the library.
- Frontend: a JavaScript web component served by the integration itself.
- Frontend-backend communication: Home Assistant WebSocket API (custom commands registered by the integration).
- Device communication: Wi-Fi, using only features already provided by the CrossPoint firmware web server.

## Configuration (config flow)

- Device address (IP or hostname, e.g. crosspoint.local), with local network discovery support (UDP port 8134, payload "hello").
- Device model, which determines the screen resolution:
  - Xteink X4: 480 x 800
  - Xteink X3: 528 x 792
  - Cross-Share: 480x800
- The model chosen here is only the fallback: when a reader is connected, its model comes from the firmware `device` status field (e.g. `xteink_x4_classic`), since several readers can share one entry.
- Path to the shared library folder (e.g. under /media), filled by the user via Samba or similar.
- Recommended subfolders: one for books, one for wallpapers.

## Library

- Files enter the library only through the shared folder (no upload from the panel).
- Periodic and on-demand scan of the folder.
- For each EPUB: extract title, author and cover from metadata.
- The panel shows the library with covers and each book's status (installed on the device or not).

## Device reachability

- The CrossPoint web server is active only while the reader is in File Transfer (or Calibre Wireless) mode.
- Core rule: if the device is unreachable, no operation on books or wallpapers is allowed. The Send and Remove buttons in the panel are disabled.
- A status sensor/entity shows whether the device is online.
- Note: the web server has no authentication; use it only on a trusted private network.

## Tracking

- Only files sent by the integration are tracked. The device is read only to reconcile (see below), never to build a catalog of its content.
- Internal store (Home Assistant storage) recording, for each transfer: file, content hash, transfer date, path on the device.
- Several readers can share one library: the connected unit is identified by the `deviceId` returned by `GET /api/status?plugin=<name>` (stable per unit). Transfers are tracked per reader, the panel shows the status of the currently connected one, and the store keeps the list of known readers. When `deviceId` is missing the hardware `serial` from the same response is used; firmware with neither falls back to a single anonymous reader. When the configured address does not answer, UDP discovery looks for the reader again (readers usually get their IP from DHCP).
- The hash detects whether a library file was modified after being sent.
- The store is updated only after the device confirms success.
- Reconciliation (when the device comes online, and with the `reconcile_device` service): tracked files that are no longer on the device are forgotten; device EPUBs in the SD card root (where books copied by hand usually are) or under the books folder that match exactly one untracked library book by file name and size are adopted (the listing has no hash, so the stored hash is the library file's).

## Book operations

- Send: upload the file to the device through the CrossPoint web server (HTTP, or the binary WebSocket protocol for fast uploads).
- Remove: request deletion through the web server (the firmware supports deleting files on the SD card). The book is marked as removed only after confirmation.
- No operation is possible while the device is offline.

## Chapter splitting

- Why: the firmware handles one spine item at a time. It inflates the whole XHTML file to the SD card and lays out all its pages before showing the first one, and redoes the layout after every font or layout change. Books with a few huge XHTML files (e.g. Project Gutenberg) make the reader wait a long time.
- Before sending (`epub_split.py`, option on by default, threshold 15,000 characters of visible text as in jtvargas/crosspoint-app), XHTML spine items above the threshold are split on a copy of the EPUB; the library file is never changed and the stored hash stays the library file's.
- Cut points: top-level headings (h1-h3) when there are at least two, merging small adjacent sections; sections still above the threshold, or files without headings, are cut between blocks by text size. Wrappers (div/section) longer than the threshold are opened so the split can happen inside them.
- Part 1 keeps the original file name; the other parts are new manifest items placed right after it in the spine. Links (XHTML, NCX, nav, OPF guide) to fragments that moved are rewritten.
- Left untouched: books with `META-INF/encryption.xml`, fixed-layout books, nav documents, and any file that fails to parse.
- Known limit: adoption during reconciliation matches the library file size, so a split book is not re-adopted if the store is lost.

## Wallpapers

- Source: image files from the wallpapers subfolder.
- Conversion in Python with Pillow: resize and crop to the selected model's resolution, grayscale, dithering.
- Two output modes, chosen when sending:
  - Normal: uncompressed 24-bit BMP, with dithering.
  - Transparent: PNG with alpha channel (overlay on top of the current screen).
- Warn the user when transparent mode is chosen for an image without transparency.
- Destination on the device: the sleep screen folder on the SD card (the firmware picks one at random when several are present).
- Note: XTC is not used; it is the pre-rendered book page format of the stock firmware.

## Reading stats widget

- The integration provides a Lovelace dashboard card showing reading statistics for one or more users, fetched from a CrossPoint Sync server.
- Server URL is configurable, defaulting to https://sync.crosspointreader.com (self-hosted instances must work too).
- Each user is configured with their CrossPoint Sync (KOSync) credentials. Authentication uses the KOSync headers x-auth-user and x-auth-key (MD5 of the password). Store credentials in the config entry, never in the frontend.
- Data source: GET /api/v1/stats/summary (combined view across devices, streaks, daily reading minutes) and GET /api/v1/stats/global (per-device snapshots).
- The backend polls the server with a DataUpdateCoordinator and exposes sensors per user (e.g. total reading time, books finished, current streak); the card reads those entities, so stats are also usable in automations and history.
- The card can show a single user or compare several users side by side.
- This feature does not depend on the e-reader being reachable: it only talks to the sync server.

## Exposed services

- send\_book
- reconcile\_device
- remove\_book
- send\_wallpaper (normal or transparent mode)
- rescan\_library
  - refresh\_reading\_stats

## Future versions

- Internationalization (i18n) of end-user messages (panel UI, notifications, config flow). Keep user-facing strings out of the code from the start so they can be translated later.

## To verify

- Exact CrossPoint web server endpoints for upload, deletion and listing (docs/webserver-endpoints.md in the crosspoint-reader repository).
- Exact path of the sleep folder and of transparent overlays in the firmware version in use.

* Exact response shape of the CrossPoint Sync stats endpoints ([docs/API.md](https://github.com/crosspoint-reader/crosspoint-sync/blob/main/docs/API.md)).
