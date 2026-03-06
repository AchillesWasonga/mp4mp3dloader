import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from watermark import DEFAULT_WATERMARK_PATH, WatermarkError, apply_watermark, resolve_path

ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = ROOT / "downloads" / "instagram"
META_DIR = ROOT / "downloads" / "instagram_meta"


class InstagramDownloadError(Exception):
    pass


def is_instagram_reel_url(url: str) -> bool:
    return bool(re.search(r"https?://(www\.)?instagram\.com/reels?/", url))


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def yt_dlp_base() -> list[str]:
    return [sys.executable, "-m", "yt_dlp"]


def resolve_output_dir(raw_output_dir: str | None) -> Path | None:
    if raw_output_dir is None:
        return None

    output_dir = Path(raw_output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    return output_dir.resolve()


def metadata_cmd(url: str, browser: Optional[str] = None) -> list[str]:
    cmd = yt_dlp_base() + [
        "--skip-download",
        "--dump-single-json",
        url,
    ]
    if browser:
        cmd.extend(["--cookies-from-browser", browser])
    return cmd


def download_cmd(
    url: str,
    browser: Optional[str] = None,
    output_dir: Path = DOWNLOADS_DIR,
) -> list[str]:
    output_template = str(output_dir / "%(uploader|unknown_creator)s - %(title)s.%(ext)s")

    cmd = yt_dlp_base() + [
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "--print",
        "after_move:filepath",
        "-o",
        output_template,
        url,
    ]
    if browser:
        cmd.extend(["--cookies-from-browser", browser])
    return cmd


def should_retry_with_cookies(stderr: str) -> bool:
    lowered = stderr.lower()
    signals = [
        "login required",
        "requested content is not available",
        "rate-limit reached",
        "main webpage is locked behind the login page",
        "unable to extract shared data",
        "unable to extract additional data",
        "instagram api is not granting access",
        "empty media response",
        "check if this post is accessible in your browser",
    ]
    return any(s in lowered for s in signals)


def cookies_help_message(browser: Optional[str]) -> str:
    if browser:
        return (
            f"Instagram blocked public access. Retry with a logged-in {browser} session "
            "or try a different browser via --browser."
        )
    return (
        "Instagram blocked public access for this reel. Choose a browser in the "
        "web app (Instagram Browser Cookies) or pass --browser "
        "{safari,chrome,firefox,edge,brave,chromium}."
    )


def fetch_metadata(url: str, browser: Optional[str] = None) -> dict:
    result = run_cmd(metadata_cmd(url, browser))
    if result.returncode != 0:
        raise InstagramDownloadError(result.stderr.strip() or result.stdout.strip())

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InstagramDownloadError(f"Could not parse metadata JSON: {exc}") from exc


def save_credit_metadata(info: dict, url: str, meta_dir: Path) -> Path:
    meta_dir.mkdir(parents=True, exist_ok=True)

    short_id = info.get("id", "unknown_id")
    payload = {
        "source_url": url,
        "id": short_id,
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader"),
        "uploader_id": info.get("uploader_id"),
        "channel": info.get("channel"),
        "timestamp": info.get("timestamp"),
        "duration": info.get("duration"),
        "webpage_url": info.get("webpage_url"),
        "extractor": info.get("extractor"),
    }

    path = meta_dir / f"{short_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def latest_video_file(output_dir: Path) -> Path | None:
    mp4_files = sorted(
        output_dir.glob("*.mp4"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return mp4_files[0] if mp4_files else None


def resolve_video_path(download_stdout: str, info: dict, video_dir: Path) -> Path:
    output_lines = [line.strip() for line in download_stdout.splitlines() if line.strip()]
    if output_lines:
        candidate = Path(output_lines[-1]).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        return candidate

    uploader = info.get("uploader") or "unknown_creator"
    title = info.get("title") or "untitled"
    guessed = video_dir / f"{uploader} - {title}.mp4"
    if guessed.exists():
        return guessed

    newest = latest_video_file(video_dir)
    return newest if newest is not None else guessed


def download_instagram_reel(
    url: str,
    browser: Optional[str] = None,
    output_dir: Optional[Path] = None,
    watermark_enabled: bool = True,
    watermark_path: Optional[Path] = None,
    watermark_position: str = "top-left",
) -> tuple[Path, Path]:
    if not is_instagram_reel_url(url):
        raise InstagramDownloadError("This script currently supports Instagram Reel URLs only.")

    if output_dir is None:
        video_dir = DOWNLOADS_DIR
        meta_dir = META_DIR
    else:
        video_dir = output_dir
        meta_dir = output_dir

    video_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # 1) Try public metadata fetch
    tried_browser = None
    try:
        info = fetch_metadata(url)
    except InstagramDownloadError as first_err:
        first_msg = str(first_err)

        if browser and should_retry_with_cookies(first_msg):
            tried_browser = browser
            info = fetch_metadata(url, browser=browser)
        elif should_retry_with_cookies(first_msg):
            raise InstagramDownloadError(cookies_help_message(browser))
        else:
            raise

    meta_path = save_credit_metadata(info, url, meta_dir)

    # 2) Try public download first unless metadata already required cookies
    if tried_browser:
        result = run_cmd(download_cmd(url, browser=tried_browser, output_dir=video_dir))
        if result.returncode != 0:
            raise InstagramDownloadError(result.stderr.strip() or result.stdout.strip())
    else:
        result = run_cmd(download_cmd(url, output_dir=video_dir))
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()

            if browser and should_retry_with_cookies(err):
                retry = run_cmd(download_cmd(url, browser=browser, output_dir=video_dir))
                if retry.returncode != 0:
                    raise InstagramDownloadError(retry.stderr.strip() or retry.stdout.strip())
                result = retry
            elif should_retry_with_cookies(err):
                raise InstagramDownloadError(cookies_help_message(browser))
            else:
                raise InstagramDownloadError(err)

    final_path = resolve_video_path(result.stdout, info, video_dir)

    if watermark_enabled:
        if watermark_path is None:
            raise InstagramDownloadError("Watermark path was not provided.")
        apply_watermark(
            video_path=final_path,
            watermark_path=watermark_path,
            position=watermark_position,
        )

    return final_path, meta_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download an Instagram Reel with optional browser-cookie fallback.")
    parser.add_argument("url", help="Instagram Reel URL")
    parser.add_argument(
        "--browser",
        choices=["safari", "chrome", "firefox", "edge", "brave", "chromium"],
        default=None,
        help="Optional browser to load cookies from if Instagram requires login/session",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for downloaded video and metadata",
    )
    parser.add_argument(
        "--no-watermark",
        action="store_true",
        help="Disable automatic watermarking",
    )
    parser.add_argument(
        "--watermark-file",
        default=str(DEFAULT_WATERMARK_PATH),
        help="PNG watermark image path (default: evalwhiteverfied.png)",
    )
    parser.add_argument(
        "--watermark-position",
        choices=["top-left", "top-right", "bottom-left", "bottom-right"],
        default="top-left",
        help="Watermark position (default: top-left)",
    )
    args = parser.parse_args()

    try:
        output_dir = resolve_output_dir(args.output_dir)
        watermark_path = resolve_path(args.watermark_file)
        if not args.no_watermark and not watermark_path.exists():
            raise InstagramDownloadError(f"Watermark file not found: {watermark_path}")

        video_path, meta_path = download_instagram_reel(
            args.url,
            browser=args.browser,
            output_dir=output_dir,
            watermark_enabled=not args.no_watermark,
            watermark_path=watermark_path,
            watermark_position=args.watermark_position,
        )
        print("Download complete.")
        print(f"Video target: {video_path}")
        print(f"Metadata saved: {meta_path}")
        if not args.no_watermark:
            print(f"Watermark applied ({args.watermark_position}): {watermark_path}")
    except WatermarkError as exc:
        print(f"Instagram download failed: {exc}")
        sys.exit(1)
    except InstagramDownloadError as exc:
        print(f"Instagram download failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
