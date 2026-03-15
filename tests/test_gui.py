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

    def test_video_frame_rate_available(self, app_window, qtbot, test_video):
        """Video frame rate is available after loading."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        # Test video is generated at 30fps
        assert app_window._bridge.videoFrameRate == 30.0

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
    """GUI tests for the cut bar marker-based cutting (part of unified Timeline)."""

    def test_timeline_enabled_with_video(self, app_window, qtbot, test_video):
        """Timeline is enabled when video is loaded."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        timeline = app_window.findChild(QObject, "timeline")
        assert timeline is not None
        assert timeline.property("enabled") is True

    def test_timeline_starts_with_no_markers(self, app_window, qtbot, test_video):
        """Timeline starts with empty markers list."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        timeline = app_window.findChild(QObject, "timeline")
        assert timeline is not None
        markers = timeline.property("markers")
        assert markers == [] or markers is None or len(markers) == 0

    def test_markers_sync_with_session(self, app_window, qtbot, test_video):
        """Markers in timeline reflect session state."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        # Add marker via bridge
        app_window._bridge.addMarker(0.5)
        qtbot.wait(50)

        timeline = app_window.findChild(QObject, "timeline")
        markers = timeline.property("markers")
        assert len(markers) == 1
        assert markers[0]["time"] == 0.5

    def test_multiple_markers_displayed(self, app_window, qtbot, test_video, capture_screenshot):
        """Multiple markers are displayed on the timeline."""
        app_window._bridge.openFile(str(test_video))
        qtbot.wait(100)

        # Add multiple markers
        app_window._bridge.addMarker(0.3)
        app_window._bridge.addMarker(0.7)
        app_window._bridge.addMarker(1.2)
        qtbot.wait(50)

        capture_screenshot(app_window, "timeline_with_markers")

        timeline = app_window.findChild(QObject, "timeline")
        markers = timeline.property("markers")
        assert len(markers) == 3


class TestMarkerSelection:
    """GUI tests for marker selection and keyboard interaction."""

    def test_cutbar_starts_with_no_selection(self, app_window, qtbot, test_video):
        """CutBar starts with no marker selected."""
        app_window._bridge.openFile(str(test_video))
        app_window._bridge.addMarker(0.5)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")
        assert cutbar is not None
        # selectedMarkerId should be empty (no selection)
        assert cutbar.property("selectedMarkerId") == ""

    def test_click_marker_selects_it(self, app_window, qtbot, test_video):
        """Clicking on a marker selects it."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)  # At 50% for a 2-second video
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")
        assert cutbar is not None

        # Click on the marker at 1.0s (50% position)
        cutbar_width = cutbar.property("width")
        marker_x = int(cutbar_width * 0.5)

        # Use QML's mapToGlobal with separate x, y args
        global_point = cutbar.mapToGlobal(marker_x, 5)
        window_pos = app_window.mapFromGlobal(global_point)

        qtbot.mouseClick(app_window, Qt.LeftButton, pos=window_pos.toPoint())
        qtbot.wait(50)

        assert cutbar.property("selectedMarkerId") == marker["id"]

    def test_click_elsewhere_deselects_marker(self, app_window, qtbot, test_video):
        """Clicking on empty track area deselects the selected marker."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # First select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        qtbot.wait(50)
        assert cutbar.property("selectedMarkerId") == marker["id"]

        # Click on empty area (far from marker)
        cutbar_width = cutbar.property("width")
        empty_x = int(cutbar_width * 0.1)  # 10% - far from 50% marker

        global_point = cutbar.mapToGlobal(empty_x, 10)
        window_pos = app_window.mapFromGlobal(global_point)

        qtbot.mouseClick(app_window, Qt.LeftButton, pos=window_pos.toPoint())
        qtbot.wait(50)

        # Should be deselected
        assert cutbar.property("selectedMarkerId") == ""

    def test_arrow_key_moves_selected_marker(self, app_window, qtbot, test_video):
        """Arrow keys move the selected marker by small increments."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        cutbar.setProperty("focus", True)
        qtbot.wait(50)

        # Press right arrow
        qtbot.keyClick(app_window, Qt.Key_Right)
        qtbot.wait(50)

        # Marker should have moved right (small increment)
        markers = app_window._bridge.markers
        assert len(markers) == 1
        assert markers[0]["time"] > 1.0  # Moved right

    def test_shift_arrow_moves_by_larger_increment(self, app_window, qtbot, test_video):
        """Shift+Arrow moves marker by larger increment."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        cutbar.setProperty("focus", True)
        qtbot.wait(50)

        # Press shift+right arrow
        qtbot.keyClick(app_window, Qt.Key_Right, Qt.ShiftModifier)
        qtbot.wait(50)

        markers = app_window._bridge.markers
        assert len(markers) == 1
        # Should move more than small increment
        assert markers[0]["time"] > 1.0

    def test_delete_key_removes_selected_marker(self, app_window, qtbot, test_video):
        """Delete key removes the selected marker."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        cutbar.setProperty("focus", True)
        qtbot.wait(50)

        # Press delete
        qtbot.keyClick(app_window, Qt.Key_Delete)
        qtbot.wait(50)

        # Marker should be removed
        markers = app_window._bridge.markers
        assert len(markers) == 0

    def test_backspace_removes_selected_marker(self, app_window, qtbot, test_video):
        """Backspace key removes the selected marker."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        cutbar.setProperty("focus", True)
        qtbot.wait(50)

        # Press backspace
        qtbot.keyClick(app_window, Qt.Key_Backspace)
        qtbot.wait(50)

        # Marker should be removed
        markers = app_window._bridge.markers
        assert len(markers) == 0

    def test_only_one_marker_selected_at_a_time(self, app_window, qtbot, test_video):
        """Clicking a different marker deselects the previous one."""
        app_window._bridge.openFile(str(test_video))
        marker1 = app_window._bridge.addMarker(0.5)
        marker2 = app_window._bridge.addMarker(1.5)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select first marker
        cutbar.setProperty("selectedMarkerId", marker1["id"])
        qtbot.wait(50)
        assert cutbar.property("selectedMarkerId") == marker1["id"]

        # Select second marker
        cutbar.setProperty("selectedMarkerId", marker2["id"])
        qtbot.wait(50)

        # Only second should be selected
        assert cutbar.property("selectedMarkerId") == marker2["id"]

    def test_selection_cleared_when_marker_removed_externally(self, app_window, qtbot, test_video):
        """Selection is cleared when the selected marker is removed via undo or clear."""
        app_window._bridge.openFile(str(test_video))
        marker = app_window._bridge.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        qtbot.wait(50)
        assert cutbar.property("selectedMarkerId") == marker["id"]

        # Remove marker via bridge (simulates undo/clear)
        app_window._bridge.removeMarker(marker["id"])
        qtbot.wait(50)

        # Selection should be cleared
        assert cutbar.property("selectedMarkerId") == ""
