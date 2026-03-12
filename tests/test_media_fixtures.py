"""Tests validating the media test infrastructure itself."""

from pathlib import Path

from conftest import (
    generate_test_video,
    get_dimensions,
    get_duration,
    get_video_stream,
)


def test_generated_fixture_has_expected_dimensions(test_video: Path):
    """Verify fixture video has the expected dimensions."""
    width, height = get_dimensions(test_video)
    assert width == 320
    assert height == 240


def test_generated_fixture_has_expected_duration(test_video: Path):
    """Verify fixture video duration is approximately correct."""
    duration = get_duration(test_video)
    assert 1.9 <= duration <= 2.1  # Allow small variance


def test_generated_fixture_has_video_stream(test_video: Path):
    """Verify the fixture has a valid video stream."""
    stream = get_video_stream(test_video)
    assert stream["codec_type"] == "video"
    assert stream["codec_name"] == "h264"


def test_can_generate_custom_dimensions(tmp_path: Path):
    """Verify we can generate videos with custom dimensions."""
    video_path = tmp_path / "custom.mp4"
    generate_test_video(video_path, duration=1.0, width=640, height=480)

    width, height = get_dimensions(video_path)
    assert width == 640
    assert height == 480


def test_can_generate_custom_duration(tmp_path: Path):
    """Verify we can generate videos with custom duration."""
    video_path = tmp_path / "short.mp4"
    generate_test_video(video_path, duration=0.5, width=160, height=120)

    duration = get_duration(video_path)
    assert 0.4 <= duration <= 0.6
