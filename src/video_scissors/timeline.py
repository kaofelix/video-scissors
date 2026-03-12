"""Timeline position calculations.

Pure functions for converting between time positions (milliseconds)
and pixel positions on the timeline. These are kept separate from
Qt/QML for testability.
"""

import math
from typing import TypedDict


class ThumbnailLayout(TypedDict):
    """Layout information for timeline thumbnails."""

    frame_count: int
    thumb_width: int
    thumb_height: int


def calculate_thumbnail_layout(
    scrubber_width: float,
    scrubber_height: float,
    video_width: int,
    video_height: int,
) -> ThumbnailLayout:
    """Calculate thumbnail layout to fill scrubber width edge-to-edge.

    Thumbnails maintain video aspect ratio with height matching scrubber height.
    Frame count is calculated to completely fill the scrubber width.

    Args:
        scrubber_width: Width of the timeline scrubber in pixels
        scrubber_height: Height of the timeline scrubber in pixels
        video_width: Original video width in pixels
        video_height: Original video height in pixels

    Returns:
        ThumbnailLayout with frame_count, thumb_width, thumb_height
    """
    if scrubber_width <= 0 or video_width <= 0 or video_height <= 0:
        return ThumbnailLayout(frame_count=0, thumb_width=0, thumb_height=0)

    # Thumbnail height matches scrubber
    thumb_height = int(scrubber_height)

    # Width preserves video aspect ratio
    aspect_ratio = video_width / video_height
    thumb_width = int(thumb_height * aspect_ratio)

    if thumb_width <= 0:
        return ThumbnailLayout(frame_count=0, thumb_width=0, thumb_height=0)

    # Calculate frame count to fill scrubber (round up)
    frame_count = math.ceil(scrubber_width / thumb_width)

    return ThumbnailLayout(
        frame_count=frame_count,
        thumb_width=thumb_width,
        thumb_height=thumb_height,
    )


def time_to_position(time_ms: float, duration_ms: float, width: float) -> float:
    """Convert time in milliseconds to pixel position.

    Args:
        time_ms: Current time position in milliseconds
        duration_ms: Total duration in milliseconds
        width: Timeline width in pixels

    Returns:
        Pixel position (0 to width), clamped to valid range
    """
    if duration_ms <= 0 or width <= 0:
        return 0

    # Clamp time to valid range
    time_ms = max(0, min(time_ms, duration_ms))

    return (time_ms / duration_ms) * width


def position_to_time(position: float, duration_ms: float, width: float) -> float:
    """Convert pixel position to time in milliseconds.

    Args:
        position: Pixel position on timeline
        duration_ms: Total duration in milliseconds
        width: Timeline width in pixels

    Returns:
        Time in milliseconds, clamped to valid range
    """
    if duration_ms <= 0 or width <= 0:
        return 0

    # Clamp position to valid range
    position = max(0, min(position, width))

    return (position / width) * duration_ms
