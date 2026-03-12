"""Test configuration and fixtures for video-scissors."""

import json
import subprocess
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def generate_test_video(
    output_path: Path,
    duration: float = 2.0,
    width: int = 320,
    height: int = 240,
    fps: int = 30,
) -> Path:
    """Generate a minimal test video using FFmpeg testsrc.

    Creates a small video with color bars pattern - suitable for testing
    crop, trim, and other operations without needing external fixtures.
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


@pytest.fixture(scope="session")
def test_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Provide a generated test video for the session."""
    video_dir = tmp_path_factory.mktemp("videos")
    video_path = video_dir / "test_320x240_2s.mp4"
    return generate_test_video(video_path, duration=2.0, width=320, height=240)


# --- Media probe helpers ---


def probe_video(path: Path) -> dict:
    """Probe video file and return metadata as dict."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=True, text=True)
    return json.loads(result.stdout)


def get_video_stream(path: Path) -> dict:
    """Get the first video stream metadata."""
    info = probe_video(path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    raise ValueError(f"No video stream found in {path}")


def get_dimensions(path: Path) -> tuple[int, int]:
    """Get video dimensions as (width, height)."""
    stream = get_video_stream(path)
    return stream["width"], stream["height"]


def get_duration(path: Path) -> float:
    """Get video duration in seconds."""
    info = probe_video(path)
    return float(info["format"]["duration"])
