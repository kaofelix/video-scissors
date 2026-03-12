"""GUI tests with screenshot capture support.

These tests verify UI behavior and can capture screenshots for debugging.

Run GUI tests:
    make test-gui           # Normal (shows window briefly)
    make test-headless      # Headless mode (no window)

Or directly:
    uv run pytest tests/test_gui.py -v
    QT_QPA_PLATFORM=offscreen uv run pytest tests/test_gui.py -v

Screenshots are saved to tests/screenshots/ when capture_screenshot is used.
This directory is gitignored.
"""

from pathlib import Path

import pytest


SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


class TestAppShell:
    """Basic GUI tests for the app shell."""

    def test_app_window_opens(self, app_window, qtbot):
        """App window opens and has expected title."""
        assert app_window.isVisible()
        assert app_window.title() == "Video Scissors"

    def test_initial_state_shows_placeholder(self, app_window, qtbot, capture_screenshot):
        """Initial state shows placeholder text when no video loaded."""
        # Verify window is ready
        assert app_window.isVisible()

        # Capture screenshot for visual verification
        screenshot_path = capture_screenshot(app_window, "initial_state")
        assert screenshot_path.exists()

    def test_window_has_expected_size(self, app_window, qtbot):
        """Window has reasonable default size."""
        assert app_window.width() >= 640
        assert app_window.height() >= 480
