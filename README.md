# MP4/MP3 Downloader

Internal tool for downloading high-quality MP4 or MP3 files from supported video URLs without using third-party downloader websites.

## MVP
- Paste one supported URL
- Download best available quality
- Output as MP4 or MP3
- Save locally
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
- watermarking
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
Youtube: python src/downloader.py "URL" --format mp4
Instagram: python src/instagram_downloader.py "URL"

Adding wrapper