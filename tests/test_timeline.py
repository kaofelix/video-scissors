"""Tests for timeline position calculations."""

from video_scissors.timeline import (
    calculate_thumbnail_layout,
    position_to_time,
    time_to_position,
)


class TestTimeToPosition:
    """Tests for converting time (ms) to pixel position."""

    def test_zero_time_returns_zero_position(self):
        assert time_to_position(time_ms=0, duration_ms=10000, width=500) == 0

    def test_full_duration_returns_full_width(self):
        assert time_to_position(time_ms=10000, duration_ms=10000, width=500) == 500

    def test_half_duration_returns_half_width(self):
        assert time_to_position(time_ms=5000, duration_ms=10000, width=500) == 250

    def test_zero_duration_returns_zero(self):
        """Edge case: no video loaded or zero-length video."""
        assert time_to_position(time_ms=0, duration_ms=0, width=500) == 0

    def test_negative_time_clamps_to_zero(self):
        assert time_to_position(time_ms=-100, duration_ms=10000, width=500) == 0

    def test_time_beyond_duration_clamps_to_width(self):
        assert time_to_position(time_ms=15000, duration_ms=10000, width=500) == 500


class TestPositionToTime:
    """Tests for converting pixel position to time (ms)."""

    def test_zero_position_returns_zero_time(self):
        assert position_to_time(position=0, duration_ms=10000, width=500) == 0

    def test_full_width_returns_full_duration(self):
        assert position_to_time(position=500, duration_ms=10000, width=500) == 10000

    def test_half_width_returns_half_duration(self):
        assert position_to_time(position=250, duration_ms=10000, width=500) == 5000

    def test_zero_width_returns_zero(self):
        """Edge case: timeline not yet laid out."""
        assert position_to_time(position=0, duration_ms=10000, width=0) == 0

    def test_zero_duration_returns_zero(self):
        """Edge case: no video loaded."""
        assert position_to_time(position=250, duration_ms=0, width=500) == 0

    def test_negative_position_clamps_to_zero(self):
        assert position_to_time(position=-50, duration_ms=10000, width=500) == 0

    def test_position_beyond_width_clamps_to_duration(self):
        assert position_to_time(position=600, duration_ms=10000, width=500) == 10000


class TestCalculateThumbnailLayout:
    """Tests for calculating thumbnail layout to fill scrubber width."""

    def test_returns_frame_count_and_dimensions(self):
        """Layout returns frame count and thumbnail dimensions."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1920,
            video_height=1080,
        )
        assert "frame_count" in layout
        assert "thumb_width" in layout
        assert "thumb_height" in layout

    def test_thumbnail_height_matches_scrubber(self):
        """Thumbnail height should match scrubber height."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1920,
            video_height=1080,
        )
        assert layout["thumb_height"] == 60

    def test_thumbnail_width_preserves_aspect_ratio(self):
        """Thumbnail width should preserve video aspect ratio."""
        # 16:9 video at 60px height -> width = 60 * (16/9) ≈ 107
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1920,
            video_height=1080,
        )
        expected_width = 60 * (1920 / 1080)
        assert layout["thumb_width"] == int(expected_width)

    def test_frame_count_fills_scrubber(self):
        """Frame count should be enough to fill scrubber width."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1920,
            video_height=1080,
        )
        # Total thumbnail width should be >= scrubber width
        total_width = layout["frame_count"] * layout["thumb_width"]
        assert total_width >= 800

    def test_frame_count_not_excessive(self):
        """Frame count should not be more than needed."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1920,
            video_height=1080,
        )
        # One less frame should not fill the scrubber
        one_less_width = (layout["frame_count"] - 1) * layout["thumb_width"]
        assert one_less_width < 800

    def test_portrait_video(self):
        """Portrait video (9:16) should have narrower thumbnails."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1080,
            video_height=1920,
        )
        # 9:16 at 60px height -> width = 60 * (9/16) ≈ 34
        expected_width = int(60 * (1080 / 1920))
        assert layout["thumb_width"] == expected_width
        # Should need more frames for portrait
        assert layout["frame_count"] > 10

    def test_square_video(self):
        """Square video should have equal width/height thumbnails."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=1080,
            video_height=1080,
        )
        assert layout["thumb_width"] == 60
        assert layout["thumb_height"] == 60

    def test_zero_scrubber_width_returns_zero_frames(self):
        """Zero scrubber width should return zero frames."""
        layout = calculate_thumbnail_layout(
            scrubber_width=0,
            scrubber_height=60,
            video_width=1920,
            video_height=1080,
        )
        assert layout["frame_count"] == 0

    def test_zero_video_dimensions_returns_zero_frames(self):
        """Zero video dimensions should return zero frames."""
        layout = calculate_thumbnail_layout(
            scrubber_width=800,
            scrubber_height=60,
            video_width=0,
            video_height=0,
        )
        assert layout["frame_count"] == 0
