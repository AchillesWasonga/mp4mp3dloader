import argparse
import shutil
import sys
import time
from pathlib import Path

import yt_dlp


BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"


def ensure_dependencies() -> None:
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is not installed or not on PATH.")
        print("Install it with: brew install ffmpeg")
        sys.exit(1)


def resolve_output_dir(raw_output_dir: str | None) -> Path:
    if raw_output_dir is None:
        return DOWNLOADS_DIR

    output_dir = Path(raw_output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    return output_dir.resolve()


def build_options(fmt: str, output_dir: Path) -> dict:
    output_template = str(output_dir / "%(title)s.%(ext)s")

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


def find_final_output_path(
    info: dict,
    ydl: yt_dlp.YoutubeDL,
    fmt: str,
    output_dir: Path,
    started_at: float,
) -> Path | None:
    expected_suffix = ".mp3" if fmt == "mp3" else ".mp4"
    candidates: list[Path] = []

    def add_candidate(path_value: str | None) -> None:
        if not path_value:
            return
        candidate = Path(path_value).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        candidates.append(candidate)

    add_candidate(info.get("filepath"))
    add_candidate(info.get("_filename"))

    for item in info.get("requested_downloads") or []:
        add_candidate(item.get("filepath"))
    for item in info.get("requested_formats") or []:
        add_candidate(item.get("filepath"))

    prepared = ydl.prepare_filename(info)
    add_candidate(prepared)
    add_candidate(str(Path(prepared).with_suffix(expected_suffix)))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    matching_files = sorted(
        output_dir.glob(f"*{expected_suffix}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for match in matching_files:
        if match.stat().st_mtime >= started_at - 5:
            return match

    return matching_files[0] if matching_files else None


def download_media(url: str, fmt: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ydl_opts = build_options(fmt, output_dir)
    started_at = time.time()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Starting download: {url}")
            print(f"Output directory: {output_dir}")
            info = ydl.extract_info(url, download=True)
            print("Done.")

            if isinstance(info, dict):
                final_path = find_final_output_path(info, ydl, fmt, output_dir, started_at)
            else:
                final_path = None

            if final_path is not None:
                print(f"Saved file: {final_path}")
            else:
                print(f"Saved file in directory: {output_dir}")
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
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for downloaded media",
    )

    args = parser.parse_args()
    output_dir = resolve_output_dir(args.output_dir)
    download_media(args.url, args.format, output_dir)


if __name__ == "__main__":
    main()
