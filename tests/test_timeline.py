"""Tests for timeline position calculations."""

from video_scissors.timeline import position_to_time, time_to_position


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
