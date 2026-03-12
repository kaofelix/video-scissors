"""FFmpeg-based edit service implementation."""

import subprocess
import uuid
from pathlib import Path

from video_scissors.services import CropRequest, CutRequest, EditResult


class FFmpegEditService:
    """Edit service implementation using FFmpeg."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def apply_crop(self, source: Path, request: CropRequest) -> EditResult:
        """Apply a crop operation to the video using FFmpeg."""
        output_path = self._output_dir / f"crop_{uuid.uuid4().hex[:8]}.mp4"

        crop_filter = f"crop={request.width}:{request.height}:{request.x}:{request.y}"

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i",
            str(source),
            "-vf",
            crop_filter,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "copy",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        return EditResult(output_path=output_path)

    def apply_cut(self, source: Path, request: CutRequest) -> EditResult:
        """Remove a time range from the video using FFmpeg.

        Keeps [0, start) and [end, duration], concatenating them.
        """
        output_path = self._output_dir / f"cut_{uuid.uuid4().hex[:8]}.mp4"

        # Build filter: trim before cut, trim after cut, concat
        filter_complex = (
            f"[0:v]trim=0:{request.start},setpts=PTS-STARTPTS[v1];"
            f"[0:v]trim={request.end},setpts=PTS-STARTPTS[v2];"
            f"[v1][v2]concat=n=2:v=1:a=0[v]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        return EditResult(output_path=output_path)
