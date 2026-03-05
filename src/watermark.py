import shutil
import subprocess
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WATERMARK_PATH = ROOT / "evalwhiteverfied.png"


class WatermarkError(Exception):
    pass


def ensure_ffmpeg_installed() -> None:
    if shutil.which("ffmpeg") is None:
        raise WatermarkError("ffmpeg is not installed or not on PATH.")


def resolve_path(path_value: str | None) -> Path:
    if path_value is None:
        return DEFAULT_WATERMARK_PATH

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def overlay_expression(position: str, padding: int) -> str:
    expr_by_position = {
        "top-left": f"{padding}:{padding}",
        "top-right": f"W-w-{padding}:{padding}",
        "bottom-left": f"{padding}:H-h-{padding}",
        "bottom-right": f"W-w-{padding}:H-h-{padding}",
    }
    try:
        return expr_by_position[position]
    except KeyError as exc:
        raise WatermarkError(f"Unsupported watermark position: {position}") from exc


def apply_watermark(
    video_path: Path,
    watermark_path: Path,
    position: str = "top-left",
    padding: int = 24,
    width_ratio: float = 0.18,
) -> Path:
    ensure_ffmpeg_installed()

    if not video_path.exists():
        raise WatermarkError(f"Video file does not exist: {video_path}")
    if not watermark_path.exists():
        raise WatermarkError(f"Watermark file does not exist: {watermark_path}")
    if width_ratio <= 0 or width_ratio >= 1:
        raise WatermarkError("Watermark width ratio must be between 0 and 1.")

    overlay = overlay_expression(position, padding)
    tmp_output = video_path.with_name(f"{video_path.stem}.wm-{uuid.uuid4().hex[:8]}{video_path.suffix}")
    ratio_expr = f"{width_ratio:.4f}"

    # Scale watermark relative to main video width, then overlay at chosen corner.
    filter_graph = (
        f"[1:v][0:v]scale2ref=w=main_w*{ratio_expr}:h=ow/mdar[wm][base];"
        f"[base][wm]overlay={overlay}[v]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(watermark_path),
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(tmp_output),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if tmp_output.exists():
            tmp_output.unlink()
        err = result.stderr.strip() or result.stdout.strip() or "Unknown ffmpeg error"
        raise WatermarkError(f"Watermarking failed: {err}")

    tmp_output.replace(video_path)
    return video_path
