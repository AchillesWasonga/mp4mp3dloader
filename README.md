# MP4 Downloader

Internal tool for downloading high-quality MP4 files from supported video URLs without using third-party downloader websites.

## MVP
- Paste one supported URL
- Download best available quality
- Output as MP4
- Save locally
- Save YouTube metadata as JSON sidecar (includes `caption`)
- Auto-apply Eval watermark to downloaded videos (default: top-left)
- Single-user internal use

## Initial Targets
- YouTube videos
- YouTube Shorts
- Instagram Reels (later / lower priority)

## Planned Stack
- yt-dlp
- ffmpeg
- lightweight custom wrapper

## Out of Scope
- captions
- reposting
- scheduling
- full workflow automation

## Goal
Provide a clean, reliable, high-quality internal alternative to ad-filled download sites.

How to open the files:

Rule of thumb

Want absolute best downloaded quality? Open with IINA/VLC

Want best Apple/iPhone compatibility? Convert to H.264 + AAC

So for maintaining the highest quality without converting, use IINA.

For instagram:

Instagram’s Terms/Help pages also warn against unauthorized scraping/automated collection, so this is best treated as an internal tool for content you have permission to reuse.


How to run it:

YouTube (default output to `downloads/`):
`./.venv/bin/python src/downloader.py "URL"`

YouTube (custom output folder):
`./.venv/bin/python src/downloader.py "URL" --output-dir /tmp/eval-test`

YouTube (custom watermark file + position):
`./.venv/bin/python src/downloader.py "URL" --watermark-file /path/to/logo.png --watermark-position top-right`

YouTube (disable watermark for one run):
`./.venv/bin/python src/downloader.py "URL" --no-watermark`

YouTube output:
- Video: `<title>.mp4`
- Metadata: `<title>.json` (includes `description` and `caption`)

Instagram (default output to `downloads/instagram` + `downloads/instagram_meta`):
`./.venv/bin/python src/instagram_downloader.py "URL"`

Instagram (custom output folder for both video + metadata):
`./.venv/bin/python src/instagram_downloader.py "URL" --output-dir /tmp/eval-test`

Instagram (custom watermark file + position):
`./.venv/bin/python src/instagram_downloader.py "URL" --watermark-file /path/to/logo.png --watermark-position top-right`

Watermark defaults:
- enabled automatically for both YouTube and Instagram downloads
- default file: `evalwhiteverfied.png` in repo root
- default position: `top-left`
- supported positions: `top-left`, `top-right`, `bottom-left`, `bottom-right`

Adding wrapper
