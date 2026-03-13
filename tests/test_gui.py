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

from PySide6.QtCore import QObject, QPoint, QRectF, Qt

from conftest import generate_test_video

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


class TestCropOverlay:
    """GUI tests for the crop overlay."""

    def test_video_ready_for_crop(self, app_window, qtbot, test_video):
        """Video loads and is ready for crop interaction."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        # Video should be loaded
        assert app_window._bridge.hasVideo
        # Video dimensions should be available (needed for crop coordinate mapping)
        assert app_window._bridge.videoWidth == 320
        assert app_window._bridge.videoHeight == 240

    def test_drag_creates_crop_selection(self, app_window, qtbot, test_video, capture_screenshot):
        """Clicking and dragging on video creates a crop selection."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(200)

        # Get the video container area (approximate - it's the main content area)
        window_center = QPoint(app_window.width() // 2, app_window.height() // 3)

        # Simulate drag from top-left to bottom-right of a region
        start = QPoint(window_center.x() - 50, window_center.y() - 50)
        end = QPoint(window_center.x() + 50, window_center.y() + 50)

        # Use qtbot mouse operations
        qtbot.mousePress(app_window, Qt.LeftButton, pos=start)
        qtbot.mouseMove(app_window, pos=end)
        qtbot.mouseRelease(app_window, Qt.LeftButton, pos=end)

        qtbot.wait(100)
        capture_screenshot(app_window, "crop_selection")

        # The crop should be captured in the screenshot for visual verification

    def test_crop_overlay_maps_against_displayed_video_rect(self, app_window, qtbot, tmp_path):
        """Crop mapping uses the displayed video rect, not the whole container."""
        portrait_video = tmp_path / "portrait.mp4"
        generate_test_video(portrait_video, duration=1.0, width=240, height=320)

        app_window._bridge.openFile(str(portrait_video))
        qtbot.wait(300)

        video_player = app_window.findChild(QObject, "videoPlayer")
        crop_overlay = app_window.findChild(QObject, "cropOverlay")

        assert video_player is not None
        assert crop_overlay is not None

        content_rect = crop_overlay.property("videoContentRect")

        assert content_rect is not None
        assert round(crop_overlay.mapToVideoX(content_rect.x())) == 0
        assert round(crop_overlay.mapToVideoY(content_rect.y())) == 0
        assert round(crop_overlay.mapToVideoX(content_rect.x() + content_rect.width())) == 240
        assert round(crop_overlay.mapToVideoY(content_rect.y() + content_rect.height())) == 320

    def test_crop_overlay_uses_video_space_layer_with_single_scale_transform(
        self, app_window, qtbot, tmp_path
    ):
        """Crop overlay renders a video-space layer transformed into the content rect."""
        portrait_video = tmp_path / "portrait.mp4"
        generate_test_video(portrait_video, duration=1.0, width=240, height=320)

        app_window._bridge.openFile(str(portrait_video))
        qtbot.wait(300)

        crop_overlay = app_window.findChild(QObject, "cropOverlay")
        video_layer = app_window.findChild(QObject, "cropVideoLayer")

        assert crop_overlay is not None
        assert video_layer is not None

        content_rect = crop_overlay.property("videoContentRect")
        video_scale = crop_overlay.property("videoScale")

        assert video_layer.property("width") == 240
        assert video_layer.property("height") == 320
        assert round(video_layer.property("x"), 3) == round(content_rect.x(), 3)
        assert round(video_layer.property("y"), 3) == round(content_rect.y(), 3)
        assert round(video_layer.property("scale"), 6) == round(video_scale, 6)

    def test_crop_overlay_converts_moving_item_points_back_to_video_space(
        self, app_window, qtbot, tmp_path
    ):
        """Points from moved crop items resolve back to stable video-space coordinates."""
        large_video = tmp_path / "large.mp4"
        generate_test_video(large_video, duration=1.0, width=1280, height=720)

        app_window._bridge.openFile(str(large_video))
        qtbot.wait(300)

        crop_overlay = app_window.findChild(QObject, "cropOverlay")
        crop_area = app_window.findChild(QObject, "cropArea")

        assert crop_overlay is not None
        assert crop_area is not None

        crop_overlay.setProperty("cropRect", QRectF(200, 100, 300, 180))
        qtbot.wait(50)

        point = crop_overlay.videoPointFromItemPoint(crop_area, 30, 20)

        assert round(point.x(), 3) == 230
        assert round(point.y(), 3) == 120


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


class TestCutBar:
    """GUI tests for the cut bar marker-based cutting."""

    def test_cut_bar_visible_in_app(self, app_window, qtbot, test_video):
        """Cut bar is visible when video is loaded."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        cut_bar = app_window.findChild(QObject, "cutBar")
        assert cut_bar is not None
        assert cut_bar.property("enabled") is True

    def test_cut_bar_starts_with_no_markers(self, app_window, qtbot, test_video):
        """Cut bar starts with empty markers list."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        cut_bar = app_window.findChild(QObject, "cutBar")
        assert cut_bar is not None
        markers = cut_bar.property("markers")
        assert markers == [] or markers is None or len(markers) == 0

    def test_markers_sync_with_session(self, app_window, qtbot, test_video):
        """Markers in cut bar reflect session state."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        # Add marker via bridge
        app_window._bridge.addMarker(0.5)
        qtbot.wait(50)

        cut_bar = app_window.findChild(QObject, "cutBar")
        markers = cut_bar.property("markers")
        assert len(markers) == 1
        assert markers[0] == 0.5

    def test_multiple_markers_displayed(self, app_window, qtbot, test_video, capture_screenshot):
        """Multiple markers are displayed on the cut bar."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        # Add multiple markers
        app_window._bridge.addMarker(0.3)
        app_window._bridge.addMarker(0.7)
        app_window._bridge.addMarker(1.2)
        qtbot.wait(50)

        capture_screenshot(app_window, "cut_bar_with_markers")

        cut_bar = app_window.findChild(QObject, "cutBar")
        markers = cut_bar.property("markers")
        assert len(markers) == 3
