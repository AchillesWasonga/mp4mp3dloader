import argparse
import shutil
import sys
from pathlib import Path

import yt_dlp


BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"


def ensure_dependencies() -> None:
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is not installed or not on PATH.")
        print("Install it with: brew install ffmpeg")
        sys.exit(1)


def build_options(fmt: str) -> dict:
    output_template = str(DOWNLOADS_DIR / "%(title)s.%(ext)s")

    if fmt == "mp4":
        return {
            "format": "bv*+ba/b",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
        }

    if fmt == "mp3":
        return {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

    raise ValueError(f"Unsupported format: {fmt}")


def download_media(url: str, fmt: str) -> None:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ydl_opts = build_options(fmt)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Starting download: {url}")
            ydl.download([url])
            print(f"Done. File saved in: {DOWNLOADS_DIR}")
    except yt_dlp.utils.DownloadError as exc:
        print(f"Download failed: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        sys.exit(1)


def main() -> None:
    ensure_dependencies()

    parser = argparse.ArgumentParser(
        description="Download a YouTube/Shorts URL as MP4 or MP3"
    )
    parser.add_argument("url", help="Video URL")
    parser.add_argument(
        "--format",
        choices=["mp4", "mp3"],
        default="mp4",
        help="Output format (default: mp4)",
    )

    args = parser.parse_args()
    download_media(args.url, args.format)


if __name__ == "__main__":
    main()