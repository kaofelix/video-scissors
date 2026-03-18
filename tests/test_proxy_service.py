"""Tests for the FFmpeg-based proxy generation service."""

import subprocess
from pathlib import Path

from conftest import generate_test_video, probe_video
from video_scissors.proxy_service import PROXY_MAX_HEIGHT, FFmpegProxyService


class TestProxyGeneration:
    """FFmpegProxyService generates ProRes proxy files."""

    def test_produces_output_file(self, test_video: Path, tmp_path: Path):
        """generate_proxy() creates a file in the output directory."""
        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()

        result = service.generate_proxy(test_video, output_dir)

        assert result.proxy_path.exists()
        assert result.proxy_path.parent == output_dir

    def test_output_is_prores_proxy_codec(self, test_video: Path, tmp_path: Path):
        """Output uses ProRes codec with proxy profile."""
        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()

        result = service.generate_proxy(test_video, output_dir)

        info = probe_video(result.proxy_path)
        video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        assert video_stream["codec_name"] == "prores"
        # Profile 0 = Proxy (apco)
        assert video_stream["profile"] == "Proxy"

    def test_output_scaled_to_max_height(self, tmp_path: Path):
        """Output height is limited to PROXY_MAX_HEIGHT, preserving aspect ratio."""
        # Create a 1080p source video
        source = tmp_path / "source_1080p.mp4"
        generate_test_video(source, duration=0.5, width=1920, height=1080)

        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()

        result = service.generate_proxy(source, output_dir)

        info = probe_video(result.proxy_path)
        video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        assert video_stream["height"] == PROXY_MAX_HEIGHT
        # Aspect ratio preserved: 1920/1080 * 720 = 1280
        assert video_stream["width"] == 1280
        # Result should also contain dimensions
        assert result.height == PROXY_MAX_HEIGHT
        assert result.width == 1280

    def test_source_smaller_than_max_not_upscaled(self, test_video: Path, tmp_path: Path):
        """Small source videos are not upscaled."""
        # test_video is 320x240, smaller than 720p
        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()

        result = service.generate_proxy(test_video, output_dir)

        info = probe_video(result.proxy_path)
        video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        # Should keep original dimensions
        assert video_stream["width"] == 320
        assert video_stream["height"] == 240
        assert result.width == 320
        assert result.height == 240

    def test_audio_stream_preserved(self, tmp_path: Path):
        """Audio stream from source is preserved in proxy."""
        # Create source with audio
        source = tmp_path / "source_with_audio.mp4"
        _generate_video_with_audio(source)

        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()

        result = service.generate_proxy(source, output_dir)

        info = probe_video(result.proxy_path)
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
        assert len(audio_streams) == 1
        assert audio_streams[0]["codec_name"] == "pcm_s16le"

    def test_source_without_audio_handled(self, test_video: Path, tmp_path: Path):
        """Source video without audio doesn't cause an error."""
        # test_video has no audio track (generated with testsrc only)
        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()

        # Should not raise
        result = service.generate_proxy(test_video, output_dir)

        assert result.proxy_path.exists()
        # Verify no audio stream in output
        info = probe_video(result.proxy_path)
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
        assert len(audio_streams) == 0

    def test_progress_callback_invoked(self, test_video: Path, tmp_path: Path):
        """Progress callback is invoked during generation."""
        service = FFmpegProxyService()
        output_dir = tmp_path / "proxies"
        output_dir.mkdir()
        progress_values: list[float] = []

        service.generate_proxy(test_video, output_dir, on_progress=progress_values.append)

        assert len(progress_values) > 0
        assert all(0.0 <= p <= 1.0 for p in progress_values)
        assert progress_values[-1] == 1.0


def _generate_video_with_audio(output_path: Path, duration: float = 0.5) -> Path:
    """Generate a test video with audio track."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=320x240:rate=30",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path
