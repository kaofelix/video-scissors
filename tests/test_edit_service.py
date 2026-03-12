"""Tests for the FFmpeg-based edit service implementation."""

from pathlib import Path

import av

from conftest import get_duration
from video_scissors.edit_service import FFmpegEditService
from video_scissors.services import CropRequest, CutRequest


class TestFFmpegEditServiceCrop:
    """Tests for crop operation using FFmpeg."""

    def test_crop_produces_output_file(self, test_video: Path, tmp_path: Path):
        """Crop operation creates an output video file."""
        service = FFmpegEditService(output_dir=tmp_path)
        request = CropRequest(x=0, y=0, width=160, height=120)

        result = service.apply_crop(test_video, request)

        assert result.output_path.exists()

    def test_crop_changes_video_dimensions(self, test_video: Path, tmp_path: Path):
        """Cropped video has the requested dimensions."""
        service = FFmpegEditService(output_dir=tmp_path)
        request = CropRequest(x=0, y=0, width=160, height=120)

        result = service.apply_crop(test_video, request)

        container = av.open(str(result.output_path))
        stream = container.streams.video[0]
        assert stream.width == 160
        assert stream.height == 120
        container.close()

    def test_crop_with_offset(self, test_video: Path, tmp_path: Path):
        """Crop can start from an offset position."""
        service = FFmpegEditService(output_dir=tmp_path)
        # test_video is 320x240, crop 160x120 from center
        request = CropRequest(x=80, y=60, width=160, height=120)

        result = service.apply_crop(test_video, request)

        container = av.open(str(result.output_path))
        stream = container.streams.video[0]
        assert stream.width == 160
        assert stream.height == 120
        container.close()

    def test_crop_preserves_duration(self, test_video: Path, tmp_path: Path):
        """Cropped video maintains original duration."""
        service = FFmpegEditService(output_dir=tmp_path)
        request = CropRequest(x=0, y=0, width=160, height=120)

        result = service.apply_crop(test_video, request)

        # Check duration is approximately the same (within 0.1s)
        original = av.open(str(test_video))
        cropped = av.open(str(result.output_path))

        assert original.duration is not None
        assert cropped.duration is not None
        orig_duration = float(original.duration) / av.time_base
        crop_duration = float(cropped.duration) / av.time_base

        original.close()
        cropped.close()

        assert abs(orig_duration - crop_duration) < 0.1

    def test_crop_output_is_valid_video(self, test_video: Path, tmp_path: Path):
        """Cropped output can be opened and has video stream."""
        service = FFmpegEditService(output_dir=tmp_path)
        request = CropRequest(x=0, y=0, width=160, height=120)

        result = service.apply_crop(test_video, request)

        container = av.open(str(result.output_path))
        assert len(container.streams.video) == 1
        container.close()


class TestFFmpegEditServiceCut:
    """Tests for cut (segment removal) operation using FFmpeg."""

    def test_cut_produces_output_file(self, test_video: Path, tmp_path: Path):
        """Cut operation creates an output video file."""
        service = FFmpegEditService(output_dir=tmp_path)
        # test_video is 2 seconds, remove middle 0.5s
        request = CutRequest(start=0.75, end=1.25)

        result = service.apply_cut(test_video, request)

        assert result.output_path.exists()

    def test_cut_reduces_duration(self, test_video: Path, tmp_path: Path):
        """Cutting removes time from the video."""
        service = FFmpegEditService(output_dir=tmp_path)
        original_duration = get_duration(test_video)
        cut_amount = 0.5  # seconds
        request = CutRequest(start=0.75, end=1.25)

        result = service.apply_cut(test_video, request)

        new_duration = get_duration(result.output_path)
        expected = original_duration - cut_amount
        assert abs(new_duration - expected) < 0.1

    def test_cut_output_is_valid_video(self, test_video: Path, tmp_path: Path):
        """Cut output can be opened and has video stream."""
        service = FFmpegEditService(output_dir=tmp_path)
        request = CutRequest(start=0.5, end=1.0)

        result = service.apply_cut(test_video, request)

        container = av.open(str(result.output_path))
        assert len(container.streams.video) == 1
        container.close()

    def test_cut_from_start(self, test_video: Path, tmp_path: Path):
        """Cut can remove from the beginning of the video."""
        service = FFmpegEditService(output_dir=tmp_path)
        original_duration = get_duration(test_video)
        request = CutRequest(start=0.0, end=0.5)

        result = service.apply_cut(test_video, request)

        new_duration = get_duration(result.output_path)
        expected = original_duration - 0.5
        assert abs(new_duration - expected) < 0.1

    def test_cut_to_end(self, test_video: Path, tmp_path: Path):
        """Cut can remove up to the end of the video."""
        service = FFmpegEditService(output_dir=tmp_path)
        original_duration = get_duration(test_video)
        request = CutRequest(start=1.5, end=original_duration)

        result = service.apply_cut(test_video, request)

        new_duration = get_duration(result.output_path)
        expected = 1.5
        assert abs(new_duration - expected) < 0.1
