# mp4mp3dloader

Internal MP4 downloader for YouTube/Shorts and Instagram Reels with optional watermarking.

## Features
- Downloads highest available quality MP4
- Supports YouTube videos, YouTube Shorts, and Instagram Reels
- Saves YouTube metadata as `<title>.json` (`description` + `caption`)
- Auto-applies watermark (default: `evalwhiteverfied.png`, `top-left`)

## Web App (Recommended)
1. Install dependencies after activating python virtual environment:
`./.venv/bin/pip install -r requirements.txt`
2. Start server:
`python src/web_app.py`
3. Open:
`http://127.0.0.1:5050`
4. Paste URL, choose platform (or `auto`), choose destination folder, set watermark options and click **Start Download**.

Note: `GET /favicon.ico 404` in Flask logs is harmless.
If Instagram fails with access/login warnings, set **Instagram Browser Cookies** to a logged-in browser (e.g., `safari` or `chrome`).

