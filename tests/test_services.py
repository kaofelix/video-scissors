"""Tests for service protocol contracts.

These tests verify that service protocols are properly defined and that
implementations can satisfy them. The protocols establish the boundaries
between high-level application logic and FFmpeg implementation details.
"""

from pathlib import Path

from video_scissors.services import (
    CropRequest,
    CutRequest,
    EditResult,
    EditService,
    ExportRequest,
    ExportService,
    MediaProbeService,
    ThumbnailRequest,
    ThumbnailService,
    VideoInfo,
)


class TestMediaProbeService:
    """Tests for the MediaProbeService protocol."""

    def test_protocol_defines_probe_method(self):
        """MediaProbeService requires a probe method returning VideoInfo."""
        # Verify it's a protocol with the expected method
        assert hasattr(MediaProbeService, "probe")

    def test_video_info_has_required_fields(self):
        """VideoInfo contains essential metadata."""
        info = VideoInfo(
            width=1920,
            height=1080,
            duration=10.5,
            codec="h264",
        )

        assert info.width == 1920
        assert info.height == 1080
        assert info.duration == 10.5
        assert info.codec == "h264"


class TestEditService:
    """Tests for the EditService protocol."""

    def test_protocol_defines_apply_crop(self):
        """EditService requires apply_crop method."""
        assert hasattr(EditService, "apply_crop")

    def test_protocol_defines_apply_cut(self):
        """EditService requires apply_cut method."""
        assert hasattr(EditService, "apply_cut")

    def test_crop_request_captures_crop_parameters(self):
        """CropRequest holds the crop box coordinates."""
        req = CropRequest(x=100, y=50, width=800, height=600)

        assert req.x == 100
        assert req.y == 50
        assert req.width == 800
        assert req.height == 600

    def test_cut_request_captures_time_range(self):
        """CutRequest holds start and end times to remove."""
        req = CutRequest(start=5.0, end=10.0)

        assert req.start == 5.0
        assert req.end == 10.0

    def test_edit_result_contains_output_path(self):
        """EditResult holds the path to the edited video."""
        result = EditResult(output_path=Path("/tmp/edited.mp4"))

        assert result.output_path == Path("/tmp/edited.mp4")


class TestThumbnailService:
    """Tests for the ThumbnailService protocol."""

    def test_protocol_defines_generate_method(self):
        """ThumbnailService requires generate method."""
        assert hasattr(ThumbnailService, "generate")

    def test_thumbnail_request_captures_parameters(self):
        """ThumbnailRequest holds timestamp and size."""
        req = ThumbnailRequest(timestamp=5.5, width=160, height=90)

        assert req.timestamp == 5.5
        assert req.width == 160
        assert req.height == 90


class TestExportService:
    """Tests for the ExportService protocol."""

    def test_protocol_defines_export_method(self):
        """ExportService requires export method."""
        assert hasattr(ExportService, "export")

    def test_export_request_captures_destination(self):
        """ExportRequest holds output path and options."""
        req = ExportRequest(
            destination=Path("/Users/me/Videos/final.mp4"),
        )

        assert req.destination == Path("/Users/me/Videos/final.mp4")
