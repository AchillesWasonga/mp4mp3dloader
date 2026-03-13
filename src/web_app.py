import re
import subprocess
import sys
from pathlib import Path

from flask import Flask, Response, render_template, request


ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
DEFAULT_OUTPUT_DIR = ROOT / "downloads"
DEFAULT_WATERMARK_FILE = ROOT / "evalwhiteverfied.png"
BROWSER_CHOICES = ["", "safari", "chrome", "firefox", "edge", "brave", "chromium"]
POSITION_CHOICES = ["top-left", "top-right", "bottom-left", "bottom-right"]
PLATFORM_CHOICES = ["auto", "youtube", "instagram"]

app = Flask(__name__, template_folder=str(SRC_DIR / "templates"))


def detect_platform(url: str) -> str | None:
    if re.search(r"(youtube\.com|youtu\.be)", url, flags=re.IGNORECASE):
        return "youtube"
    if re.search(r"instagram\.com/reels?/", url, flags=re.IGNORECASE):
        return "instagram"
    return None


def available_watermark_files() -> list[str]:
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
    found: list[str] = []
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_file():
                found.append(str(path.resolve()))
    return sorted(set(found))


def run_download_command(cmd: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = "\n".join(
        part for part in [result.stdout.strip(), result.stderr.strip()] if part
    ).strip()
    if not combined:
        combined = "(No output)"
    return result.returncode == 0, combined


def last_meaningful_line(log: str) -> str:
    lines = [line.strip() for line in log.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def extract_saved_paths(log: str) -> list[tuple[str, str]]:
    extracted: list[tuple[str, str]] = []
    labels = {
        "Saved file:": "Video",
        "Video target:": "Video",
        "Metadata saved:": "Metadata",
    }
    for line in log.splitlines():
        stripped = line.strip()
        for prefix, label in labels.items():
            if stripped.startswith(prefix):
                extracted.append((label, stripped.removeprefix(prefix).strip()))
    return extracted


def instagram_access_blocked(log: str) -> bool:
    lowered = log.lower()
    signals = [
        "instagram api is not granting access",
        "empty media response",
        "check if this post is accessible in your browser",
        "login required",
        "blocked public access",
    ]
    return any(s in lowered for s in signals)


def instagram_source_unavailable(log: str) -> bool:
    lowered = log.lower()
    signals = [
        "requested content is not available",
        "page isn't available",
        "page may have been removed",
        "the link you followed may be broken",
    ]
    return any(s in lowered for s in signals)


def build_result_payload(
    ok: bool,
    platform: str,
    browser: str,
    output_dir: str,
    watermark_enabled: bool,
    log: str,
    command: str,
) -> dict:
    payload = {
        "ok": ok,
        "title": "",
        "message": "",
        "command": command,
        "log": log,
        "saved_paths": extract_saved_paths(log),
        "tips": [],
        "technical_note": last_meaningful_line(log),
        "output_dir": output_dir or str(DEFAULT_OUTPUT_DIR),
    }

    lowered = log.lower()

    if ok:
        payload["title"] = "Download complete"
        payload["message"] = (
            "Your video was downloaded successfully."
            if not watermark_enabled
            else "Your video was downloaded and watermarked successfully."
        )
        if not payload["saved_paths"]:
            payload["tips"] = [
                f"Check the destination folder: {payload['output_dir']}",
            ]
        return payload

    if "watermark file not found" in lowered:
        payload["title"] = "Watermark file not found"
        payload["message"] = "The watermark image path does not exist."
        payload["tips"] = [
            "Choose a valid watermark file path or select a detected preset.",
            "If you do not need a watermark for this run, turn off 'Enable watermark'.",
        ]
        return payload

    if "ffmpeg is not installed" in lowered:
        payload["title"] = "ffmpeg is missing"
        payload["message"] = "The app cannot process video without ffmpeg installed."
        payload["tips"] = [
            "Install ffmpeg on this machine and retry.",
            "On macOS with Homebrew: brew install ffmpeg",
        ]
        return payload

    if "supports instagram reel urls only" in lowered:
        payload["title"] = "Instagram URL not supported"
        payload["message"] = "Use a direct Instagram reel URL."
        payload["tips"] = [
            "Paste a link that looks like instagram.com/reel/... or instagram.com/reels/...",
        ]
        return payload

    if platform == "instagram" and instagram_source_unavailable(log):
        payload["title"] = "Instagram reel unavailable"
        payload["message"] = "Instagram is reporting that this reel is not available."
        payload["tips"] = [
            "Open the reel in a browser first. If Instagram shows 'page isn't available', the source is gone or restricted.",
            "Ask for a fresh URL if the post may have been removed or changed.",
        ]
        return payload

    if platform == "instagram" and instagram_access_blocked(log):
        payload["title"] = "Instagram login required"
        if browser:
            payload["message"] = (
                f"Instagram would not serve this reel through the selected {browser} session."
            )
            payload["tips"] = [
                f"Make sure you are logged into Instagram in {browser} on this machine.",
                "Open the reel in that same browser and confirm it plays there.",
                "If it still fails, try a different browser from the dropdown.",
            ]
        else:
            payload["message"] = "Instagram would not serve this reel anonymously."
            payload["tips"] = [
                "Choose Safari or Chrome in 'Instagram Browser Cookies'.",
                "Make sure that browser is already logged into Instagram.",
                "Then retry the download.",
            ]
        return payload

    if "watermarking failed" in lowered:
        payload["title"] = "Watermark step failed"
        payload["message"] = "The video downloaded, but the watermark step did not complete."
        payload["tips"] = [
            "Retry once to rule out a transient ffmpeg issue.",
            "If the problem continues, try disabling watermark for this run.",
        ]
        return payload

    if "download failed" in lowered:
        payload["title"] = "Download failed"
        payload["message"] = "The source did not complete successfully."
        payload["tips"] = [
            "Double-check the URL and try again.",
            "If this is Instagram, test whether the reel opens in a browser first.",
        ]
        return payload

    payload["title"] = "Something went wrong"
    payload["message"] = "The app could not complete this request."
    payload["tips"] = [
        "Review the technical details below.",
        "Retry once after confirming the URL and form values.",
    ]
    return payload


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status=204)


@app.route("/", methods=["GET", "POST"])
def index():
    state = {
        "url": "",
        "platform": "auto",
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "watermark_enabled": True,
        "watermark_file": str(DEFAULT_WATERMARK_FILE),
        "watermark_position": "top-left",
        "browser": "",
    }
    result = {
        "ok": None,
        "title": "",
        "message": "",
        "log": "",
        "command": "",
        "saved_paths": [],
        "tips": [],
        "technical_note": "",
        "output_dir": str(DEFAULT_OUTPUT_DIR),
    }

    if request.method == "POST":
        state["url"] = request.form.get("url", "").strip()
        state["platform"] = request.form.get("platform", "auto").strip()
        state["output_dir"] = request.form.get("output_dir", "").strip()
        state["watermark_enabled"] = request.form.get("watermark_enabled") == "on"
        state["watermark_file"] = request.form.get("watermark_file", "").strip()
        state["watermark_position"] = request.form.get(
            "watermark_position",
            "top-left",
        ).strip()
        state["browser"] = request.form.get("browser", "").strip()

        if not state["url"]:
            result["ok"] = False
            result["title"] = "Video URL is required"
            result["message"] = "Please provide a video URL."
        elif state["platform"] not in PLATFORM_CHOICES:
            result["ok"] = False
            result["title"] = "Platform value is invalid"
            result["message"] = "Invalid platform option."
        elif state["watermark_position"] not in POSITION_CHOICES:
            result["ok"] = False
            result["title"] = "Watermark position is invalid"
            result["message"] = "Invalid watermark position."
        elif state["browser"] not in BROWSER_CHOICES:
            result["ok"] = False
            result["title"] = "Browser value is invalid"
            result["message"] = "Invalid browser option."
        else:
            detected_platform = detect_platform(state["url"])
            selected_platform = state["platform"]
            if selected_platform == "auto":
                detected = detected_platform
                if detected is None:
                    result["ok"] = False
                    result["title"] = "Platform not recognized"
                    result["message"] = (
                        "Could not auto-detect platform from URL. "
                        "Choose YouTube or Instagram manually."
                    )
                    detected = None
                selected_platform = detected
            elif detected_platform and detected_platform != selected_platform:
                result["ok"] = False
                result["title"] = "Platform does not match URL"
                result["message"] = (
                    f"This URL looks like {detected_platform}, but the form is set to "
                    f"{selected_platform}. Change the platform or paste a matching URL."
                )

            if selected_platform is not None and result["ok"] is None:
                if selected_platform == "youtube":
                    cmd = [sys.executable, str(SRC_DIR / "downloader.py"), state["url"]]
                else:
                    cmd = [
                        sys.executable,
                        str(SRC_DIR / "instagram_downloader.py"),
                        state["url"],
                    ]
                    if state["browser"]:
                        cmd.extend(["--browser", state["browser"]])

                if state["output_dir"]:
                    cmd.extend(["--output-dir", state["output_dir"]])

                if state["watermark_enabled"]:
                    watermark_file = state["watermark_file"]
                    watermark_path = Path(watermark_file).expanduser()
                    if not watermark_path.is_absolute():
                        watermark_path = (ROOT / watermark_path).resolve()
                    if not watermark_path.exists():
                        result["ok"] = False
                        result["title"] = "Watermark file not found"
                        result["message"] = f"Watermark file not found: {watermark_path}"
                    else:
                        cmd.extend(["--watermark-file", str(watermark_path)])
                        cmd.extend(["--watermark-position", state["watermark_position"]])
                else:
                    cmd.append("--no-watermark")

                if result["ok"] is None:
                    result["command"] = " ".join(cmd)
                    ok, log = run_download_command(cmd)
                    result = build_result_payload(
                        ok=ok,
                        platform=selected_platform,
                        browser=state["browser"],
                        output_dir=state["output_dir"],
                        watermark_enabled=state["watermark_enabled"],
                        log=log,
                        command=result["command"],
                    )

        if result["ok"] is False and not result["title"]:
            result["title"] = "Please review the form"
        if result["ok"] is False and not result["technical_note"]:
            result["technical_note"] = result["message"]

    return render_template(
        "index.html",
        state=state,
        result=result,
        platform_choices=PLATFORM_CHOICES,
        position_choices=POSITION_CHOICES,
        browser_choices=BROWSER_CHOICES,
        watermark_files=available_watermark_files(),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
