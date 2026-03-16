"""Tests for thumbnail extraction service."""

from pathlib import Path

from PIL import Image

from video_scissors.document import CropRect
from video_scissors.thumbnails import ThumbnailExtractor


class TestThumbnailExtractor:
    """Tests for PyAV-based thumbnail extraction."""

    def test_extract_single_frame(self, test_video: Path, tmp_path: Path):
        """Can extract a single frame from a video."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(test_video, frame_count=1, thumb_height=60)

        assert len(frames) == 1
        assert frames[0].exists()
        assert frames[0].suffix == ".jpg"

    def test_extract_multiple_frames(self, test_video: Path, tmp_path: Path):
        """Can extract multiple frames evenly distributed."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(test_video, frame_count=5, thumb_height=60)

        assert len(frames) == 5
        for frame_path in frames:
            assert frame_path.exists()

    def test_frames_have_correct_height(self, test_video: Path, tmp_path: Path):
        """Extracted frames have the requested height."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(test_video, frame_count=1, thumb_height=60)

        img = Image.open(frames[0])
        assert img.height == 60

    def test_frames_preserve_aspect_ratio(self, test_video: Path, tmp_path: Path):
        """Extracted frames preserve video aspect ratio."""
        # Test video is 320x240 (4:3 aspect ratio)
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(test_video, frame_count=1, thumb_height=60)

        img = Image.open(frames[0])
        # 4:3 at 60 height -> width should be 80
        expected_width = int(60 * (320 / 240))
        assert img.width == expected_width

    def test_caches_extracted_frames(self, test_video: Path, tmp_path: Path):
        """Second extraction returns cached frames without re-extracting."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)

        # First extraction
        frames1 = extractor.extract(test_video, frame_count=3, thumb_height=60)

        # Second extraction should return same paths
        frames2 = extractor.extract(test_video, frame_count=3, thumb_height=60)

        assert frames1 == frames2

    def test_different_frame_count_extracts_new(self, test_video: Path, tmp_path: Path):
        """Different frame count triggers new extraction."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)

        frames1 = extractor.extract(test_video, frame_count=3, thumb_height=60)
        frames2 = extractor.extract(test_video, frame_count=5, thumb_height=60)

        assert len(frames1) == 3
        assert len(frames2) == 5
        assert frames1 != frames2

    def test_returns_empty_list_for_zero_frames(self, test_video: Path, tmp_path: Path):
        """Requesting zero frames returns empty list."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(test_video, frame_count=0, thumb_height=60)

        assert frames == []

    def test_returns_empty_for_nonexistent_file(self, tmp_path: Path):
        """Returns empty list for nonexistent video file."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(tmp_path / "nonexistent.mp4", frame_count=5, thumb_height=60)

        assert frames == []


class TestThumbnailExtractorCrop:
    """Tests for cropped thumbnail extraction."""

    def test_cropped_frame_has_crop_aspect_ratio(self, test_video: Path, tmp_path: Path):
        """Cropped thumbnails use the crop region's aspect ratio."""
        # Test video is 320x240. Crop a 200x100 region (2:1 aspect).
        crop = CropRect(x=40, y=30, width=200, height=100)
        extractor = ThumbnailExtractor(cache_dir=tmp_path)
        frames = extractor.extract(test_video, frame_count=1, thumb_height=60, crop=crop)

        assert len(frames) == 1
        img = Image.open(frames[0])
        assert img.height == 60
        # 2:1 aspect at 60px height -> 120px wide
        assert img.width == 120

    def test_cropped_frames_differ_from_uncropped(self, test_video: Path, tmp_path: Path):
        """Cropped and uncropped extractions produce different images."""
        crop = CropRect(x=40, y=30, width=200, height=100)
        extractor = ThumbnailExtractor(cache_dir=tmp_path)

        uncropped = extractor.extract(test_video, frame_count=1, thumb_height=60)
        cropped = extractor.extract(test_video, frame_count=1, thumb_height=60, crop=crop)

        # Different cache entries (different paths)
        assert uncropped[0] != cropped[0]

        # Different image dimensions
        img_uncropped = Image.open(uncropped[0])
        img_cropped = Image.open(cropped[0])
        assert img_uncropped.width != img_cropped.width

    def test_different_crops_produce_different_cache_entries(
        self, test_video: Path, tmp_path: Path
    ):
        """Different crop rects are cached separately."""
        crop1 = CropRect(x=0, y=0, width=160, height=120)
        crop2 = CropRect(x=80, y=60, width=160, height=120)
        extractor = ThumbnailExtractor(cache_dir=tmp_path)

        frames1 = extractor.extract(test_video, frame_count=1, thumb_height=60, crop=crop1)
        frames2 = extractor.extract(test_video, frame_count=1, thumb_height=60, crop=crop2)

        assert frames1[0] != frames2[0]

    def test_crop_none_same_as_no_crop(self, test_video: Path, tmp_path: Path):
        """Passing crop=None behaves the same as omitting it."""
        extractor = ThumbnailExtractor(cache_dir=tmp_path)

        frames_default = extractor.extract(test_video, frame_count=1, thumb_height=60)
        frames_none = extractor.extract(test_video, frame_count=1, thumb_height=60, crop=None)

        assert frames_default == frames_none
