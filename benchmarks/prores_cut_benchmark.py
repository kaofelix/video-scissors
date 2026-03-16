#!/usr/bin/env python3
"""Benchmark ProRes proxy generation and cut operations.

Compares:
1. ProRes proxy generation time
2. Cut via re-encoding (full transcode)
3. Cut via stream-copy (no re-encode, possible with all-intra codecs)

Usage:
    python benchmarks/prores_cut_benchmark.py [--duration SECONDS]
"""

import argparse
import subprocess
import tempfile
import time
from pathlib import Path


def run_ffmpeg(args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run FFmpeg command and return result."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    return subprocess.run(cmd, capture_output=capture_output, check=True)


def generate_test_source(output: Path, duration: int, resolution: str = "1920x1080") -> None:
    """Generate a test video using FFmpeg's testsrc."""
    width, height = resolution.split("x")
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={duration}:size={resolution}:rate=30",
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
            str(output),
        ]
    )


def generate_prores_proxy(source: Path, output: Path, max_height: int = 720) -> float:
    """Transcode to ProRes 422 Proxy. Returns time in seconds."""
    start = time.perf_counter()
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-c:v",
            "prores_ks",
            "-profile:v",
            "0",  # Proxy profile
            "-vf",
            f"scale=-2:{max_height}",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    return time.perf_counter() - start


def cut_via_reencode(source: Path, output: Path, cut_start: float, cut_end: float) -> float:
    """Apply cut by re-encoding. Returns time in seconds."""
    # Keep [0, cut_start) and [cut_end, end], concatenate
    filter_complex = (
        f"[0:v]trim=0:{cut_start},setpts=PTS-STARTPTS[v1];"
        f"[0:a]atrim=0:{cut_start},asetpts=PTS-STARTPTS[a1];"
        f"[0:v]trim={cut_end},setpts=PTS-STARTPTS[v2];"
        f"[0:a]atrim={cut_end},asetpts=PTS-STARTPTS[a2];"
        f"[v1][a1][v2][a2]concat=n=2:v=1:a=1[v][a]"
    )
    start = time.perf_counter()
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "0",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    return time.perf_counter() - start


def cut_via_streamcopy(
    source: Path, output: Path, cut_start: float, cut_end: float, temp_dir: Path
) -> float:
    """Apply cut by stream-copying segments (no re-encode). Returns time in seconds."""
    seg1 = temp_dir / "seg1.mov"
    seg2 = temp_dir / "seg2.mov"
    concat_list = temp_dir / "concat.txt"

    start = time.perf_counter()

    # Extract segment before cut
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-t",
            str(cut_start),
            "-c",
            "copy",
            str(seg1),
        ]
    )

    # Extract segment after cut
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-ss",
            str(cut_end),
            "-c",
            "copy",
            str(seg2),
        ]
    )

    # Create concat demuxer file
    concat_list.write_text(f"file '{seg1}'\nfile '{seg2}'\n")

    # Concatenate
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(output),
        ]
    )

    return time.perf_counter() - start


def get_duration(path: Path) -> float:
    """Get video duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def format_time(seconds: float) -> str:
    """Format time in human-readable form."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


def main():
    parser = argparse.ArgumentParser(description="Benchmark ProRes proxy cut operations")
    parser.add_argument(
        "--duration", type=int, default=120, help="Test video duration in seconds (default: 120)"
    )
    parser.add_argument(
        "--resolution", default="1920x1080", help="Source resolution (default: 1920x1080)"
    )
    parser.add_argument("--proxy-height", type=int, default=720, help="Proxy height (default: 720)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        source = tmp / "source.mp4"
        proxy = tmp / "proxy.mov"
        cut_reencode = tmp / "cut_reencode.mov"
        cut_streamcopy = tmp / "cut_streamcopy.mov"

        print("=== ProRes Proxy Cut Benchmark ===\n")
        print("Parameters:")
        print(f"  Source duration: {args.duration}s")
        print(f"  Source resolution: {args.resolution}")
        print(f"  Proxy height: {args.proxy_height}p")
        print()

        # Generate test source
        print("Generating test source video...", end=" ", flush=True)
        t_start = time.perf_counter()
        generate_test_source(source, args.duration, args.resolution)
        t_source = time.perf_counter() - t_start
        source_size = source.stat().st_size / (1024 * 1024)
        print(f"done ({format_time(t_source)}, {source_size:.1f}MB)")

        # Generate ProRes proxy
        print("Generating ProRes proxy...", end=" ", flush=True)
        t_proxy = generate_prores_proxy(source, proxy, args.proxy_height)
        proxy_size = proxy.stat().st_size / (1024 * 1024)
        print(f"done ({format_time(t_proxy)}, {proxy_size:.1f}MB)")

        # Define cut region (middle third of video)
        cut_start = args.duration / 3
        cut_end = 2 * args.duration / 3
        cut_duration = cut_end - cut_start
        print(f"\nCut region: {cut_start:.1f}s - {cut_end:.1f}s (removing {cut_duration:.1f}s)")
        print()

        # Cut via re-encoding
        print("Cut via re-encoding (full transcode)...", end=" ", flush=True)
        t_reencode = cut_via_reencode(proxy, cut_reencode, cut_start, cut_end)
        reencode_size = cut_reencode.stat().st_size / (1024 * 1024)
        reencode_duration = get_duration(cut_reencode)
        print(
            f"done ({format_time(t_reencode)}, {reencode_size:.1f}MB, "
            f"{reencode_duration:.1f}s output)"
        )

        # Cut via stream-copy
        print("Cut via stream-copy (no re-encode)...", end=" ", flush=True)
        t_streamcopy = cut_via_streamcopy(proxy, cut_streamcopy, cut_start, cut_end, tmp)
        streamcopy_size = cut_streamcopy.stat().st_size / (1024 * 1024)
        streamcopy_duration = get_duration(cut_streamcopy)
        print(
            f"done ({format_time(t_streamcopy)}, {streamcopy_size:.1f}MB, "
            f"{streamcopy_duration:.1f}s output)"
        )

        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"{'Operation':<35} {'Time':>10}")
        print("-" * 50)
        print(f"{'ProRes proxy generation':<35} {format_time(t_proxy):>10}")
        print(f"{'Cut via re-encoding':<35} {format_time(t_reencode):>10}")
        print(f"{'Cut via stream-copy':<35} {format_time(t_streamcopy):>10}")
        print("-" * 50)
        speedup = t_reencode / t_streamcopy if t_streamcopy > 0 else float("inf")
        print(f"{'Stream-copy speedup':<35} {speedup:>9.1f}x")
        print()

        # Interpretation
        print("INTERPRETATION")
        print("-" * 50)
        if t_streamcopy < 0.5:
            print("✓ Stream-copy cuts are fast enough to feel instant (<500ms)")
            print("  → Can apply cuts to proxy without EDL complexity")
        elif t_streamcopy < 2.0:
            print("⚠ Stream-copy cuts are noticeable but tolerable (<2s)")
            print("  → Could work, but consider EDL for better UX")
        else:
            print("✗ Stream-copy cuts are too slow (>2s)")
            print("  → EDL approach recommended for instant editing")

        if t_reencode < 2.0:
            print(f"✓ Re-encoding is also viable at {format_time(t_reencode)}")
        else:
            print(f"⚠ Re-encoding at {format_time(t_reencode)} may feel sluggish")


if __name__ == "__main__":
    main()
