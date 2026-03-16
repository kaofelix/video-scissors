#!/usr/bin/env python3
"""Benchmark ProRes proxy crop operations.

Crops require re-encoding (can't stream-copy), but let's see how fast
ProRes re-encoding is compared to H.264.

Usage:
    python benchmarks/prores_crop_benchmark.py [--duration SECONDS]
"""

import argparse
import subprocess
import tempfile
import time
from pathlib import Path


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    """Run FFmpeg command and return result."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    return subprocess.run(cmd, capture_output=True, check=True)


def generate_prores_proxy(output: Path, duration: int, height: int = 720) -> None:
    """Generate a ProRes proxy directly from testsrc."""
    width = int(height * 16 / 9)  # Assume 16:9
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={duration}:size={width}x{height}:rate=30",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "0",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def crop_prores(source: Path, output: Path, x: int, y: int, w: int, h: int) -> float:
    """Apply crop to ProRes, outputting ProRes. Returns time in seconds."""
    start = time.perf_counter()
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-vf",
            f"crop={w}:{h}:{x}:{y}",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "0",
            "-c:a",
            "copy",
            str(output),
        ]
    )
    return time.perf_counter() - start


def crop_h264(source: Path, output: Path, x: int, y: int, w: int, h: int) -> float:
    """Apply crop outputting H.264 (current approach). Returns time in seconds."""
    start = time.perf_counter()
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-vf",
            f"crop={w}:{h}:{x}:{y}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "copy",
            str(output),
        ]
    )
    return time.perf_counter() - start


def format_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


def main():
    parser = argparse.ArgumentParser(description="Benchmark ProRes proxy crop operations")
    parser.add_argument("--duration", type=int, default=120, help="Test video duration in seconds")
    parser.add_argument("--proxy-height", type=int, default=720, help="Proxy height (default: 720)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        proxy = tmp / "proxy.mov"
        crop_prores_out = tmp / "crop_prores.mov"
        crop_h264_out = tmp / "crop_h264.mp4"

        print("=== ProRes Proxy Crop Benchmark ===\n")
        print("Parameters:")
        print(f"  Duration: {args.duration}s")
        print(f"  Proxy height: {args.proxy_height}p")
        print()

        # Generate ProRes proxy directly
        print("Generating ProRes proxy...", end=" ", flush=True)
        t_start = time.perf_counter()
        generate_prores_proxy(proxy, args.duration, args.proxy_height)
        t_proxy = time.perf_counter() - t_start
        proxy_size = proxy.stat().st_size / (1024 * 1024)
        print(f"done ({format_time(t_proxy)}, {proxy_size:.1f}MB)")

        # Crop parameters (center crop to 50% size)
        width = int(args.proxy_height * 16 / 9)
        crop_w = width // 2
        crop_h = args.proxy_height // 2
        crop_x = width // 4
        crop_y = args.proxy_height // 4
        print(f"\nCrop: {crop_w}x{crop_h} at ({crop_x}, {crop_y})")
        print()

        # Crop with ProRes output
        print("Crop → ProRes output...", end=" ", flush=True)
        t_prores = crop_prores(proxy, crop_prores_out, crop_x, crop_y, crop_w, crop_h)
        prores_size = crop_prores_out.stat().st_size / (1024 * 1024)
        print(f"done ({format_time(t_prores)}, {prores_size:.1f}MB)")

        # Crop with H.264 output (current approach for comparison)
        print("Crop → H.264 output (current)...", end=" ", flush=True)
        t_h264 = crop_h264(proxy, crop_h264_out, crop_x, crop_y, crop_w, crop_h)
        h264_size = crop_h264_out.stat().st_size / (1024 * 1024)
        print(f"done ({format_time(t_h264)}, {h264_size:.1f}MB)")

        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"{'Operation':<35} {'Time':>10}")
        print("-" * 50)
        print(f"{'Crop → ProRes':<35} {format_time(t_prores):>10}")
        print(f"{'Crop → H.264 (current)':<35} {format_time(t_h264):>10}")
        print("-" * 50)

        print()
        print("INTERPRETATION")
        print("-" * 50)
        print("Crops REQUIRE re-encoding (can't stream-copy).")
        print()
        if t_prores < 2.0:
            print(f"✓ ProRes crop at {format_time(t_prores)} is tolerable")
        else:
            print(f"⚠ ProRes crop at {format_time(t_prores)} may feel sluggish")
            print("  → Consider QML clipping for instant preview, encode on export")


if __name__ == "__main__":
    main()
