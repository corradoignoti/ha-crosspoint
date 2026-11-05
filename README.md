# CrossPoint for Home Assistant

A custom Home Assistant integration that manages a library of books and wallpapers
and sends them over Wi-Fi to an e-reader running the
[CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) firmware,
keeping track of what has been installed on the device.

## Supported devices

| Model       | Resolution |
|-------------|------------|
| Xteink X4   | 480 × 800  |
| Xteink X3   | 528 × 792  |
| Cross-Share | 480 × 800  |

## Installation (HACS)

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/corradoignoti/ha-crosspoint` with category **Integration**.
3. Install **CrossPoint** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → CrossPoint**.

## Features

- **Library panel**: a **CrossPoint** entry in the sidebar (admin users only)
  shows your books with cover, title and author, and your wallpapers. Each item
  shows whether it is on the e-reader, and whether the library file was modified
  after it was sent. Both tabs have a search box.
- **Books**: send EPUB files to the e-reader and remove them again. Title,
  author and cover are read from the EPUB metadata.
- **Wallpapers**: images are resized, cropped and converted to the screen
  resolution of your model, then sent as a sleep screen. Two modes:
  - *Normal*: opaque 24-bit BMP with dithering.
  - *Transparent*: PNG with alpha channel, drawn on top of the current screen.
    You are warned if the image has no transparency.
- **Tracking**: only files sent by the integration are tracked (path on the
  device, content hash, transfer date). The e-reader is never scanned to build a
  catalog. Use **Sync with device** in the panel (or `reconcile_device`) to
  forget tracked files that were deleted on the reader and to adopt books
  already on it that match a library book by file name and size.
- **Online sensor**: a binary sensor tells whether the e-reader is reachable.
  When it is offline, every Send and Remove action is disabled. The reader is
  reachable only while it is in File Transfer (or Calibre Wireless) mode.
- **Other entities**: Wi-Fi signal, number of books in the library, number of
  books on the device.
- **Reading stats**: reading statistics from a CrossPoint Sync server, as
  sensors and as a dashboard card (see [Reading stats](#reading-stats-card)).
  This does not need the e-reader to be online.

### Services

All services take a `config_entry_id` (the e-reader). File names are relative to
the books or wallpapers subfolder of the library.

| Service                 | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| `send_book`             | Upload a book. `overwrite` replaces a file not sent by Home Assistant.      |
| `remove_book`           | Delete a book sent by Home Assistant. `forget_missing` stops tracking it.   |
| `send_wallpaper`        | Convert and upload an image. `mode`: `normal` or `transparent`; `force` sends a transparent overlay even without transparency. |
| `remove_wallpaper`      | Delete a wallpaper sent by Home Assistant.                                  |
| `rescan_library`        | Scan the library folder now (it is also scanned periodically).              |
| `reconcile_device`      | Compare tracked files with the e-reader content (needs File Transfer mode). |
| `refresh_reading_stats` | Fetch the reading statistics from CrossPoint Sync now.                      |

## Configuration

Add the integration from **Settings → Devices & services → Add integration →
CrossPoint**. Readers answering on the local network are discovered
automatically and offered in a list; you can also enter the address by hand.

1. **Device**
   - **Address**: IP or hostname of the reader (for example `crosspoint.local`).
   - **Model**: Xteink X4, Xteink X3 or Cross-Share. It determines the wallpaper
     resolution.

   The reader does not need to be in File Transfer mode to save the
   configuration: if it is unreachable you are asked to submit again to save the
   address anyway.
2. **Library folder**
   - **Library folder**: an absolute path Home Assistant can access, for example
     `/media/crosspoint` (anything under `/media`, or a folder listed in
     `allowlist_external_dirs`). Share it through Samba or similar and copy your
     files into it; there is no upload from the panel.
   - **Books** and **wallpapers** subfolders: created if missing (defaults
     `books` and `wallpapers`).

Afterwards, **Configure** on the integration lets you change:

- **Library scan interval** (default 30 minutes).
- **Books folder on the device**: where books are sent on the SD card (default
  `/Books`).

Address, model and library folder can be changed with **Reconfigure**.

### Reading stats users

Reading stats come from a [CrossPoint Sync](https://github.com/crosspoint-reader/crosspoint-sync)
server. Each person is a separate entry under the integration:

1. Open the CrossPoint integration and choose **Add reading stats user**.
2. Enter the **Server URL** (default `https://sync.crosspointreader.com`;
   self-hosted servers work too), the **username** and the **password** of the
   CrossPoint Sync (KOSync) account.
3. Repeat for every user you want to track.

Only the hashed password is stored, in the Home Assistant config entry. If the
server rejects the credentials later, a repair issue asks you to reconfigure the
user.

Each user gets these sensors: reading time, pages read, books finished, reading
sessions, current streak, longest streak and last upload. You can use them in
automations and history like any other entity.

## Widgets

### Library panel

Nothing to add: the **CrossPoint** entry appears in the sidebar as soon as the
integration is set up. If you have more than one e-reader, pick it at the top of
the panel.

### Reading stats card

The card is loaded automatically by the integration; you do not need to add a
dashboard resource. Add it from the dashboard editor: **Add card → CrossPoint
reading stats**, or paste this in the YAML editor:

```yaml
type: custom:crosspoint-stats-card
```

With no options the card shows every configured reading stats user: a single
user is shown alone, several users are compared side by side, with the best
value of each statistic highlighted. Options:

| Option  | Description                                                              |
|---------|--------------------------------------------------------------------------|
| `title` | Card title. Default: *Reading stats*.                                    |
| `users` | List of user names to show, in order. Default: all configured users.     |

```yaml
type: custom:crosspoint-stats-card
title: Family reading
users:
  - alice
  - bob
```

If the card does not appear in the card picker after an update, reload the
browser page with the cache cleared.

## Security

The CrossPoint web server has no authentication, and it is active only while the
reader is in File Transfer (or Calibre Wireless) mode. Use it only on a trusted
private network.

## Development

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv -r requirements_test.txt
uv pip install --python .venv "$(.venv/bin/python scripts/frontend_requirement.py)"
.venv/bin/ruff check . && .venv/bin/pytest
```

## License

[MIT](LICENSE)

The integration icon is the CrossPoint icon from
[crosspoint-reader](https://github.com/crosspoint-reader/crosspoint-reader),
© 2025 CrossPoint Reader organization, used under the MIT License.
