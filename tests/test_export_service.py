"""Tests for the FFmpeg-based export service."""

from pathlib import Path

import av

from conftest import get_duration
from video_scissors.document import EditSpec
from video_scissors.export_service import FFmpegExportService


class TestExportNoop:
    """Export with no edits copies the source."""

    def test_produces_output_file(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"

        service.export(test_video, EditSpec(), output)

        assert output.exists()

    def test_preserves_duration(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"

        service.export(test_video, EditSpec(), output)

        assert abs(get_duration(output) - get_duration(test_video)) < 0.1

    def test_preserves_dimensions(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"

        service.export(test_video, EditSpec(), output)

        container = av.open(str(output))
        stream = container.streams.video[0]
        assert stream.width == 320
        assert stream.height == 240
        container.close()


class TestExportCrop:
    """Export with crop only."""

    def test_changes_dimensions(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_crop(0, 0, 160, 120)

        service.export(test_video, spec, output)

        container = av.open(str(output))
        stream = container.streams.video[0]
        assert stream.width == 160
        assert stream.height == 120
        container.close()

    def test_preserves_duration(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_crop(0, 0, 160, 120)

        service.export(test_video, spec, output)

        assert abs(get_duration(output) - get_duration(test_video)) < 0.1


class TestExportCuts:
    """Export with cuts only."""

    def test_single_cut_reduces_duration(self, test_video: Path, tmp_path: Path):
        """Cutting 0.5s from a 2s video produces ~1.5s output."""
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_cut(0.5, 1.0)

        service.export(test_video, spec, output)

        assert abs(get_duration(output) - 1.5) < 0.15

    def test_multiple_cuts(self, test_video: Path, tmp_path: Path):
        """Multiple cuts are applied together."""
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_cut(0.25, 0.5).with_cut(1.0, 1.25)

        service.export(test_video, spec, output)

        # 2.0 - 0.25 - 0.25 = 1.5
        assert abs(get_duration(output) - 1.5) < 0.15

    def test_cut_from_start(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_cut(0.0, 0.5)

        service.export(test_video, spec, output)

        assert abs(get_duration(output) - 1.5) < 0.15

    def test_cut_to_end(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_cut(1.5, 2.0)

        service.export(test_video, spec, output)

        assert abs(get_duration(output) - 1.5) < 0.15

    def test_preserves_dimensions(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_cut(0.5, 1.0)

        service.export(test_video, spec, output)

        container = av.open(str(output))
        stream = container.streams.video[0]
        assert stream.width == 320
        assert stream.height == 240
        container.close()


class TestExportCutsAndCrop:
    """Export with both cuts and crop."""

    def test_applies_both(self, test_video: Path, tmp_path: Path):
        """Output has reduced duration and changed dimensions."""
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        spec = EditSpec().with_cut(0.5, 1.0).with_crop(0, 0, 160, 120)

        service.export(test_video, spec, output)

        container = av.open(str(output))
        stream = container.streams.video[0]
        assert stream.width == 160
        assert stream.height == 120
        container.close()
        assert abs(get_duration(output) - 1.5) < 0.15


class TestExportProgress:
    """Progress callback behavior."""

    def test_progress_callback_invoked(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        progress_values: list[float] = []

        service.export(test_video, EditSpec(), output, on_progress=progress_values.append)

        assert len(progress_values) > 0
        assert all(0.0 <= p <= 1.0 for p in progress_values)

    def test_progress_reaches_completion(self, test_video: Path, tmp_path: Path):
        service = FFmpegExportService()
        output = tmp_path / "out.mp4"
        progress_values: list[float] = []

        service.export(test_video, EditSpec(), output, on_progress=progress_values.append)

        assert progress_values[-1] == 1.0
