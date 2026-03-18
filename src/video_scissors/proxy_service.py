"""FFmpeg-based proxy generation service.

Transcodes source video to ProRes 422 Proxy for fast seeking and editing.
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

from video_scissors.services import ProxyResult

PROXY_MAX_HEIGHT = 720


class FFmpegProxyService:
    """Proxy service that generates ProRes 422 Proxy files using FFmpeg."""

    def generate_proxy(
        self,
        source: Path,
        output_dir: Path,
        on_progress: Callable[[float], None] | None = None,
    ) -> ProxyResult:
        """Generate a ProRes proxy from the source video."""
        output_path = output_dir / f"proxy_{uuid.uuid4().hex[:8]}.mov"

        # Get source info for scaling and progress
        source_width, source_height = _probe_dimensions(source)
        source_duration = _probe_duration(source)

        # Build command with optional scaling
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
        ]

        if source_height > PROXY_MAX_HEIGHT:
            # Scale down, preserving aspect ratio (-2 ensures even width)
            cmd += ["-vf", f"scale=-2:{PROXY_MAX_HEIGHT}"]

        cmd += [
            "-c:v",
            "prores_ks",
            "-profile:v",
            "0",  # Proxy profile
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

        _run_ffmpeg(cmd, source_duration, on_progress)

        # Get actual output dimensions
        width, height = _probe_dimensions(output_path)
        return ProxyResult(proxy_path=output_path, width=width, height=height)


def _probe_dimensions(path: Path) -> tuple[int, int]:
    """Get video dimensions via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    info = json.loads(result.stdout)
    stream = info["streams"][0]
    return stream["width"], stream["height"]


def _probe_duration(path: Path) -> float:
    """Get video duration via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _run_ffmpeg(
    cmd: list[str],
    duration: float,
    on_progress: Callable[[float], None] | None,
) -> None:
    """Run FFmpeg, optionally parsing progress."""
    if on_progress is None:
        subprocess.run(cmd, capture_output=True, check=True)
        return

    if duration <= 0:
        subprocess.run(cmd, capture_output=True, check=True)
        on_progress(1.0)
        return

    # Run with progress parsing from stderr
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert process.stderr is not None
    stderr = process.stderr
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    buf = ""

    for chunk in iter(lambda: stderr.read(256), ""):
        buf += chunk
        for match in time_pattern.finditer(buf):
            h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
            elapsed = h * 3600 + m * 60 + s
            progress = min(elapsed / duration, 0.99)
            on_progress(progress)
        if len(buf) > 1024:
            buf = buf[-512:]

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

    on_progress(1.0)
