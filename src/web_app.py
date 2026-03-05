import re
import subprocess
import sys
from pathlib import Path

from flask import Flask, render_template, request


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
    if re.search(r"instagram\.com/reel/", url, flags=re.IGNORECASE):
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
        "message": "",
        "log": "",
        "command": "",
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
            result["message"] = "Please provide a video URL."
        elif state["platform"] not in PLATFORM_CHOICES:
            result["ok"] = False
            result["message"] = "Invalid platform option."
        elif state["watermark_position"] not in POSITION_CHOICES:
            result["ok"] = False
            result["message"] = "Invalid watermark position."
        elif state["browser"] not in BROWSER_CHOICES:
            result["ok"] = False
            result["message"] = "Invalid browser option."
        else:
            selected_platform = state["platform"]
            if selected_platform == "auto":
                detected = detect_platform(state["url"])
                if detected is None:
                    result["ok"] = False
                    result["message"] = (
                        "Could not auto-detect platform from URL. "
                        "Choose YouTube or Instagram manually."
                    )
                    detected = None
                selected_platform = detected

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
                        result["message"] = f"Watermark file not found: {watermark_path}"
                    else:
                        cmd.extend(["--watermark-file", str(watermark_path)])
                        cmd.extend(["--watermark-position", state["watermark_position"]])
                else:
                    cmd.append("--no-watermark")

                if result["ok"] is None:
                    result["command"] = " ".join(cmd)
                    ok, log = run_download_command(cmd)
                    result["ok"] = ok
                    result["message"] = (
                        "Download completed successfully." if ok else "Download failed."
                    )
                    result["log"] = log

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
