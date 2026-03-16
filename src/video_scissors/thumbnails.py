"""Thumbnail extraction service using PyAV.

Extracts frames from video files for timeline display.
Uses in-memory caching to avoid re-extraction during a session.
"""

from __future__ import annotations

from pathlib import Path

import av

from video_scissors.document import CropRect


class ThumbnailExtractor:
    """Extracts video thumbnails using PyAV with in-memory caching."""

    def __init__(self, cache_dir: Path):
        """Initialize extractor with output directory.

        Args:
            cache_dir: Directory for storing extracted frame images
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[tuple, list[Path]] = {}

    def extract(
        self,
        video_path: Path,
        frame_count: int,
        thumb_height: int,
        crop: CropRect | None = None,
    ) -> list[Path]:
        """Extract frames from video, evenly distributed across duration.

        Results are cached in memory for the session.

        Args:
            video_path: Path to the video file
            frame_count: Number of frames to extract
            thumb_height: Height of thumbnails (width calculated from aspect ratio)
            crop: Optional crop region to apply before resizing

        Returns:
            List of paths to extracted JPEG frames, or empty list on error
        """
        if frame_count <= 0:
            return []

        if not video_path.exists():
            return []

        # Check in-memory cache (crop is part of the key)
        crop_key = (crop.x, crop.y, crop.width, crop.height) if crop else None
        cache_key = (str(video_path), frame_count, thumb_height, crop_key)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Extract frames
        try:
            frames = self._extract_frames(video_path, frame_count, thumb_height, crop)
            self._cache[cache_key] = frames
            return frames
        except Exception:
            return []

    def _extract_frames(
        self,
        video_path: Path,
        frame_count: int,
        thumb_height: int,
        crop: CropRect | None = None,
    ) -> list[Path]:
        """Extract frames using PyAV.

        Decodes video sequentially and picks frames at even intervals.
        This is more reliable than seeking, which only works with keyframes.
        """
        # Create subdirectory for this extraction
        crop_suffix = f"_crop{crop.x}_{crop.y}_{crop.width}_{crop.height}" if crop else ""
        subdir = self.cache_dir / f"{video_path.stem}_{frame_count}_{thumb_height}{crop_suffix}"
        subdir.mkdir(parents=True, exist_ok=True)

        container = av.open(str(video_path))
        stream = container.streams.video[0]

        # Calculate thumbnail dimensions from crop region or full frame
        aspect_ratio = crop.width / crop.height if crop else stream.width / stream.height
        thumb_width = int(thumb_height * aspect_ratio)

        # Calculate which frame indices to extract
        total_frames = stream.frames
        if total_frames == 0 and stream.duration and stream.time_base and stream.average_rate:
            # Estimate from duration if frame count not available
            duration = float(stream.duration * stream.time_base)
            fps = float(stream.average_rate)
            total_frames = int(duration * fps)

        if total_frames == 0:
            total_frames = frame_count  # Fallback

        # Calculate target frame indices (evenly distributed)
        target_indices = [int(i * total_frames / frame_count) for i in range(frame_count)]

        frame_paths: list[Path] = []
        next_target_idx = 0

        for frame_idx, frame in enumerate(container.decode(stream)):
            if next_target_idx >= len(target_indices):
                break

            if frame_idx >= target_indices[next_target_idx]:
                frame_path = subdir / f"frame_{next_target_idx:04d}.jpg"

                # Convert to PIL, optionally crop, then resize
                img = frame.to_image()
                if crop:
                    img = img.crop((crop.x, crop.y, crop.x + crop.width, crop.y + crop.height))
                img = img.resize((thumb_width, thumb_height))

                # Save as JPEG
                img.save(frame_path, "JPEG", quality=85)
                frame_paths.append(frame_path)
                next_target_idx += 1

        container.close()
        return frame_paths
