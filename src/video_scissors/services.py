"""Service protocols and data types.

These protocols define the boundaries between high-level application
logic and FFmpeg implementation details. Application code depends on
these abstractions, not on FFmpeg directly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from video_scissors.document import CropRect, EditSpec

# --- Data Types ---


@dataclass(frozen=True)
class VideoInfo:
    """Metadata about a video file."""

    width: int
    height: int
    duration: float
    codec: str


@dataclass(frozen=True)
class ThumbnailRequest:
    """Parameters for thumbnail generation."""

    timestamp: float
    width: int
    height: int


@dataclass(frozen=True)
class ExportRequest:
    """Parameters for exporting the final video."""

    destination: Path


# --- Service Protocols ---


class MediaProbeService(Protocol):
    """Service for probing video metadata."""

    def probe(self, path: Path) -> VideoInfo:
        """Probe a video file and return its metadata."""
        ...


class ThumbnailService(Protocol):
    """Service for generating video thumbnails."""

    def generate(self, source: Path, request: ThumbnailRequest) -> Path:
        """Generate a thumbnail image at the specified timestamp."""
        ...


class ExportService(Protocol):
    """Service for rendering an EditSpec to a final output file."""

    def export(
        self,
        source: Path,
        edit_spec: EditSpec,
        output: Path,
        on_progress: Callable[[float], None] | None = None,
    ) -> None:
        """Render edit_spec applied to source, write to output."""
        ...


class ThumbnailExtractorProtocol(Protocol):
    """Protocol for thumbnail extraction services."""

    def extract(
        self,
        video_path: Path,
        frame_count: int,
        thumb_height: int,
        crop: CropRect | None = None,
    ) -> list[Path]:
        """Extract frames from video, evenly distributed across duration."""
        ...
