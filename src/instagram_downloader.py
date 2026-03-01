import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = ROOT / "downloads" / "instagram"
META_DIR = ROOT / "downloads" / "instagram_meta"


class InstagramDownloadError(Exception):
    pass


def is_instagram_reel_url(url: str) -> bool:
    return bool(re.search(r"https?://(www\.)?instagram\.com/reel/", url))


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def yt_dlp_base() -> list[str]:
    return [sys.executable, "-m", "yt_dlp"]


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
    ]
    return any(s in lowered for s in signals)


def fetch_metadata(url: str, browser: Optional[str] = None) -> dict:
    result = run_cmd(metadata_cmd(url, browser))
    if result.returncode != 0:
        raise InstagramDownloadError(result.stderr.strip() or result.stdout.strip())

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InstagramDownloadError(f"Could not parse metadata JSON: {exc}") from exc


def save_credit_metadata(info: dict, url: str) -> Path:
    META_DIR.mkdir(parents=True, exist_ok=True)

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

    path = META_DIR / f"{short_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def download_instagram_reel(url: str, browser: Optional[str] = None) -> tuple[Path, Path]:
    if not is_instagram_reel_url(url):
        raise InstagramDownloadError("This script currently supports Instagram Reel URLs only.")

    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Try public metadata fetch
    tried_browser = None
    try:
        info = fetch_metadata(url)
    except InstagramDownloadError as first_err:
        first_msg = str(first_err)

        if browser and should_retry_with_cookies(first_msg):
            tried_browser = browser
            info = fetch_metadata(url, browser=browser)
        else:
            raise

    meta_path = save_credit_metadata(info, url)

    # 2) Try public download first unless metadata already required cookies
    if tried_browser:
        result = run_cmd(download_cmd(url, browser=tried_browser))
        if result.returncode != 0:
            raise InstagramDownloadError(result.stderr.strip() or result.stdout.strip())
    else:
        result = run_cmd(download_cmd(url))
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()

            if browser and should_retry_with_cookies(err):
                retry = run_cmd(download_cmd(url, browser=browser))
                if retry.returncode != 0:
                    raise InstagramDownloadError(retry.stderr.strip() or retry.stdout.strip())
            else:
                raise InstagramDownloadError(err)

    # Best-effort guess of final path from metadata
    uploader = info.get("uploader") or "unknown_creator"
    title = info.get("title") or "untitled"
    final_path = DOWNLOADS_DIR / f"{uploader} - {title}.mp4"

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
    args = parser.parse_args()

    try:
        video_path, meta_path = download_instagram_reel(args.url, browser=args.browser)
        print("Download complete.")
        print(f"Video target: {video_path}")
        print(f"Metadata saved: {meta_path}")
    except InstagramDownloadError as exc:
        print(f"Instagram download failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()