# CrossPoint for Home Assistant

A custom Home Assistant integration that manages a library of books and wallpapers
and sends them over Wi-Fi to an e-reader running the
[CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) firmware,
keeping track of what has been installed on the device.

> **Status:** early development. Not ready for use yet.

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

## Configuration

- **Address**: IP or hostname of the reader (for example `crosspoint.local`).
  Devices on the local network are discovered automatically.
- **Model**: determines the wallpaper resolution.
- **Library folder**: a folder Home Assistant can access (for example
  `/media/crosspoint`), filled through Samba or similar. The `books` and
  `wallpapers` subfolders are created if missing.

## Security

The CrossPoint web server has no authentication, and it is active only while the
reader is in File Transfer (or Calibre Wireless) mode. Use it only on a trusted
private network.

## Development

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv -r requirements_test.txt
.venv/bin/ruff check . && .venv/bin/pytest
```

## License

[MIT](LICENSE)

The integration icon is the CrossPoint icon from
[crosspoint-reader](https://github.com/crosspoint-reader/crosspoint-reader),
© 2025 CrossPoint Reader organization, used under the MIT License.
