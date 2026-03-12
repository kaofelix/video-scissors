"""Thumbnail extraction service using PyAV.

Extracts frames from video files for timeline display.
Frames are cached to avoid repeated extraction.
"""

import hashlib
from pathlib import Path

import av


class ThumbnailExtractor:
    """Extracts and caches video thumbnails using PyAV."""

    def __init__(self, cache_dir: Path):
        """Initialize extractor with cache directory.

        Args:
            cache_dir: Directory for storing extracted frame images
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract(
        self,
        video_path: Path,
        frame_count: int,
        thumb_height: int,
    ) -> list[Path]:
        """Extract frames from video, evenly distributed across duration.

        Args:
            video_path: Path to the video file
            frame_count: Number of frames to extract
            thumb_height: Height of thumbnails (width calculated from aspect ratio)

        Returns:
            List of paths to extracted JPEG frames, or empty list on error
        """
        if frame_count <= 0:
            return []

        if not video_path.exists():
            return []

        # Check cache first
        cache_key = self._cache_key(video_path, frame_count, thumb_height)
        cached = self._get_cached(cache_key, frame_count)
        if cached:
            return cached

        # Extract frames
        try:
            return self._extract_frames(video_path, frame_count, thumb_height, cache_key)
        except Exception:
            return []

    def _cache_key(self, video_path: Path, frame_count: int, thumb_height: int) -> str:
        """Generate cache key from video path and extraction parameters."""
        # Include file mtime to invalidate cache if video changes
        stat = video_path.stat()
        key_data = f"{video_path}:{stat.st_mtime}:{frame_count}:{thumb_height}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]

    def _get_cached(self, cache_key: str, frame_count: int) -> list[Path] | None:
        """Check if frames are already cached."""
        cache_subdir = self.cache_dir / cache_key
        if not cache_subdir.exists():
            return None

        frames = sorted(cache_subdir.glob("frame_*.jpg"))
        if len(frames) == frame_count:
            return frames
        return None

    def _extract_frames(
        self,
        video_path: Path,
        frame_count: int,
        thumb_height: int,
        cache_key: str,
    ) -> list[Path]:
        """Extract frames using PyAV."""
        cache_subdir = self.cache_dir / cache_key
        cache_subdir.mkdir(parents=True, exist_ok=True)

        container = av.open(str(video_path))
        stream = container.streams.video[0]

        # Calculate duration and timestamps (in seconds)
        duration = float(stream.duration * stream.time_base)
        timestamps = [i * duration / frame_count for i in range(frame_count)]

        # Calculate thumbnail dimensions
        aspect_ratio = stream.width / stream.height
        thumb_width = int(thumb_height * aspect_ratio)

        frame_paths = []
        for i, timestamp in enumerate(timestamps):
            frame_path = cache_subdir / f"frame_{i:04d}.jpg"

            # Seek to timestamp (convert seconds to microseconds for av.time_base)
            # Use backward seek to find nearest keyframe, then decode forward
            seek_ts = int(timestamp * av.time_base.denominator)
            container.seek(seek_ts, backward=True, any_frame=False)

            # Decode frames until we reach or pass our target timestamp
            target_pts = int(timestamp / stream.time_base)
            for frame in container.decode(stream):
                if frame.pts >= target_pts or frame.pts == 0:
                    # Convert to PIL and resize
                    img = frame.to_image()
                    img = img.resize((thumb_width, thumb_height))

                    # Save as JPEG
                    img.save(frame_path, "JPEG", quality=85)
                    frame_paths.append(frame_path)
                    break

        container.close()
        return frame_paths
