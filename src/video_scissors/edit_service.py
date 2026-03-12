"""FFmpeg-based edit service implementation."""

import subprocess
import uuid
from pathlib import Path

from video_scissors.services import CropRequest, EditResult


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
