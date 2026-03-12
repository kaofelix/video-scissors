"""Timeline position calculations.

Pure functions for converting between time positions (milliseconds)
and pixel positions on the timeline. These are kept separate from
Qt/QML for testability.
"""


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
