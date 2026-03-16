"""FFmpeg-based export service — renders EditSpec to a final output file."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from video_scissors.document import EditSpec, effective_duration


class FFmpegExportService:
    """Export service that renders an EditSpec to a video file using FFmpeg.

    This is the single place where FFmpeg encoding happens during the
    editing workflow. All non-destructive edits (cuts, crop) are applied
    in one pass to produce the final output.
    """

    def export(
        self,
        source: Path,
        edit_spec: EditSpec,
        output: Path,
        on_progress: Callable[[float], None] | None = None,
    ) -> None:
        """Render edit_spec applied to source, write to output."""
        source_duration = _probe_duration(source)
        has_audio = _has_audio_stream(source)
        cmd = _build_ffmpeg_command(source, edit_spec, output, source_duration, has_audio)
        _run_ffmpeg(cmd, source_duration, edit_spec, on_progress)


def _probe_duration(source: Path) -> float:
    """Get source video duration via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _has_audio_stream(source: Path) -> bool:
    """Check if source video contains an audio stream."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(source),
        ],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _build_ffmpeg_command(
    source: Path,
    edit_spec: EditSpec,
    output: Path,
    source_duration: float,
    has_audio: bool,
) -> list[str]:
    """Build the FFmpeg command for the given edit spec."""
    cuts = sorted(edit_spec.cuts, key=lambda c: c.start)
    crop = edit_spec.crop
    has_cuts = len(cuts) > 0
    has_crop = crop is not None

    if not has_cuts and not has_crop:
        # No edits — simple copy
        return [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-c",
            "copy",
            str(output),
        ]

    if not has_cuts and has_crop:
        # Crop only — simple filter
        assert crop is not None
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
        ]
        if has_audio:
            cmd += ["-c:a", "copy"]
        cmd.append(str(output))
        return cmd

    # Cuts (with optional crop) — build filter_complex
    # Compute kept segments (inverse of cuts)
    segments = _kept_segments(cuts, source_duration)
    n = len(segments)

    crop_suffix = ""
    if has_crop:
        assert crop is not None
        crop_suffix = f",crop={crop.width}:{crop.height}:{crop.x}:{crop.y}"

    # Build video filter chains
    v_parts: list[str] = []
    a_parts: list[str] = []
    v_labels: list[str] = []
    a_labels: list[str] = []

    for i, (start, end) in enumerate(segments):
        vl = f"[v{i}]"
        v_parts.append(f"[0:v]trim={start}:{end},setpts=PTS-STARTPTS{crop_suffix}{vl}")
        v_labels.append(vl)

        if has_audio:
            al = f"[a{i}]"
            a_parts.append(f"[0:a]atrim={start}:{end},asetpts=PTS-STARTPTS{al}")
            a_labels.append(al)

    # Concat
    v_concat = "".join(v_labels) + f"concat=n={n}:v=1:a=0[vout]"
    parts = v_parts + a_parts + [v_concat]
    maps = ["-map", "[vout]"]

    if has_audio:
        a_concat = "".join(a_labels) + f"concat=n={n}:v=0:a=1[aout]"
        parts.append(a_concat)
        maps += ["-map", "[aout]"]

    filter_complex = ";".join(parts)

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        filter_complex,
        *maps,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        str(output),
    ]


def _kept_segments(
    cuts: list,
    source_duration: float,
) -> list[tuple[float, float]]:
    """Compute the kept time segments (inverse of sorted cuts)."""
    segments: list[tuple[float, float]] = []
    pos = 0.0
    for cut in cuts:
        if cut.start > pos:
            segments.append((pos, cut.start))
        pos = cut.end
    if pos < source_duration:
        segments.append((pos, source_duration))
    return segments


def _run_ffmpeg(
    cmd: list[str],
    source_duration: float,
    edit_spec: EditSpec,
    on_progress: Callable[[float], None] | None,
) -> None:
    """Run FFmpeg, optionally parsing progress."""
    if on_progress is None:
        subprocess.run(cmd, capture_output=True, check=True)
        return

    # Run with progress parsing from stderr
    # FFmpeg writes "time=HH:MM:SS.ss" lines to stderr
    target_duration = effective_duration(source_duration, edit_spec)
    if target_duration <= 0:
        subprocess.run(cmd, capture_output=True, check=True)
        on_progress(1.0)
        return

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert process.stderr is not None
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    buf = ""

    for chunk in iter(lambda: process.stderr.read(256), ""):
        buf += chunk
        # Parse time= from latest content
        for match in time_pattern.finditer(buf):
            h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
            elapsed = h * 3600 + m * 60 + s
            progress = min(elapsed / target_duration, 0.99)
            on_progress(progress)
        # Keep only tail to avoid unbounded buffer
        if len(buf) > 1024:
            buf = buf[-512:]

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

    on_progress(1.0)
