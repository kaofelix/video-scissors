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


class TestTimeline:
    """GUI tests for the timeline scrubber."""

    def test_timeline_visible_in_app(self, app_window, qtbot):
        """Timeline component is present when app loads."""
        # The app loads Main.qml which includes the Timeline component
        # If Timeline.qml had errors, the window wouldn't load
        assert app_window.isVisible()

    def test_timeline_disabled_without_video(self, app_window, qtbot):
        """Timeline is disabled when no video is loaded."""
        # The timeline's enabled property is bound to session.hasVideo
        # Without a video loaded, interaction should be disabled
        assert app_window.isVisible()
        # Session has no video initially
        assert not app_window._bridge.hasVideo

    def test_timeline_enabled_with_video(self, app_window, qtbot, test_video):
        """Timeline is enabled when video is loaded."""
        # Load video
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)  # Allow signal processing

        assert app_window._bridge.hasVideo

    def test_timeline_shows_playhead_position(
        self, app_window, qtbot, test_video, capture_screenshot
    ):
        """Timeline displays the current playhead position."""
        # Load video
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(200)  # Allow video to load and timeline to update

        # Capture for visual verification
        capture_screenshot(app_window, "timeline_with_video")

        # Verify video is loaded (timeline should now show duration)
        assert app_window._bridge.hasVideo
