"""Service protocols and data types.

These protocols define the boundaries between high-level application
logic and FFmpeg implementation details. Application code depends on
these abstractions, not on FFmpeg directly.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# --- Data Types ---


@dataclass(frozen=True)
class VideoInfo:
    """Metadata about a video file."""

    width: int
    height: int
    duration: float
    codec: str


@dataclass(frozen=True)
class CropRequest:
    """Parameters for a crop operation."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class CutRequest:
    """Parameters for cutting/removing a time range."""

    start: float
    end: float


@dataclass(frozen=True)
class EditResult:
    """Result of an edit operation."""

    output_path: Path


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


class EditService(Protocol):
    """Service for applying edit operations."""

    def apply_crop(self, source: Path, request: CropRequest) -> EditResult:
        """Apply a crop operation to the video."""
        ...

    def apply_cut(self, source: Path, request: CutRequest) -> EditResult:
        """Remove a time range from the video."""
        ...


class ThumbnailService(Protocol):
    """Service for generating video thumbnails."""

    def generate(self, source: Path, request: ThumbnailRequest) -> Path:
        """Generate a thumbnail image at the specified timestamp."""
        ...


class ExportService(Protocol):
    """Service for exporting the final video."""

    def export(self, source: Path, request: ExportRequest) -> Path:
        """Export the video to the destination."""
        ...
