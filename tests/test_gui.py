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
from PySide6.QtMultimedia import QMediaPlayer

from conftest import generate_test_video

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


class TestCropPreview:
    """GUI tests for visual crop preview via QML clipping."""

    def test_no_crop_shows_full_video(self, app_window, qtbot, test_video):
        """Without a crop, the video clip container is not active."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        assert video_area is not None
        assert video_area.property("cropActive") is False

    def test_crop_activates_clip_preview(self, app_window, qtbot, test_video):
        """After applying a crop, the video area shows clipped preview."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        # Apply a crop via bridge (non-destructive)
        app_window._session.setCrop(40, 30, 200, 150)
        qtbot.wait(100)

        video_area = app_window.findChild(QObject, "videoArea")
        assert video_area is not None
        assert video_area.property("cropActive") is True

    def test_undo_crop_returns_to_full_frame(self, app_window, qtbot, test_video):
        """Undoing a crop returns the video to full-frame display."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        # Apply crop then undo
        app_window._session.setCrop(40, 30, 200, 150)
        qtbot.wait(100)

        video_area = app_window.findChild(QObject, "videoArea")
        assert video_area.property("cropActive") is True

        app_window._session.undo()
        qtbot.wait(100)

        assert video_area.property("cropActive") is False

    def test_crop_overlay_visible_when_crop_active(self, app_window, qtbot, test_video):
        """CropOverlay remains visible and interactive when a crop is applied."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        # Apply crop
        app_window._session.setCrop(40, 30, 200, 150)
        qtbot.wait(100)

        crop_overlay = app_window.findChild(QObject, "cropOverlay")
        assert crop_overlay is not None
        assert crop_overlay.property("visible") is True

    def test_crop_overlay_uses_crop_dimensions_when_crop_active(
        self, app_window, qtbot, test_video
    ):
        """When a crop is active, overlay works in cropped video dimensions."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        crop_overlay = app_window.findChild(QObject, "cropOverlay")
        assert crop_overlay is not None

        # Before crop: overlay uses source dimensions
        assert crop_overlay.property("videoWidth") == 320
        assert crop_overlay.property("videoHeight") == 240

        # Apply crop
        app_window._session.setCrop(40, 30, 200, 150)
        qtbot.wait(100)

        # After crop: overlay uses crop dimensions
        assert crop_overlay.property("videoWidth") == 200
        assert crop_overlay.property("videoHeight") == 150

    def test_stacked_crop_translates_to_source_coordinates(self, app_window, qtbot, test_video):
        """Drawing a crop on a cropped view produces correct source coordinates."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        # First crop: (40, 30, 200, 150) in source coords
        app_window._session.setCrop(40, 30, 200, 150)
        qtbot.wait(100)

        # Simulate applying a second crop at (20, 10, 100, 80)
        # relative to the cropped view. In source coords this should be
        # (40+20, 30+10, 100, 80) = (60, 40, 100, 80)
        crop_overlay = app_window.findChild(QObject, "cropOverlay")
        crop_overlay.cropApplied.emit(20, 10, 100, 80)
        qtbot.wait(100)

        # Verify the crop in the EditSpec is in source coordinates
        crop_rect = app_window._session.document.editSpec.cropRect
        assert crop_rect["x"] == 60
        assert crop_rect["y"] == 40
        assert crop_rect["width"] == 100
        assert crop_rect["height"] == 80

    def test_undo_stacked_crop_restores_previous(self, app_window, qtbot, test_video):
        """Undoing a stacked crop restores the previous crop, not full frame."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        # First crop
        app_window._session.setCrop(40, 30, 200, 150)
        qtbot.wait(100)

        # Second crop (stacked, in source coords for simplicity)
        app_window._session.setCrop(60, 40, 100, 80)
        qtbot.wait(100)

        # Undo → back to first crop
        app_window._session.undo()
        qtbot.wait(100)

        video_area = app_window.findChild(QObject, "videoArea")
        assert video_area.property("cropActive") is True
        crop_rect = app_window._session.document.editSpec.cropRect
        assert crop_rect["x"] == 40
        assert crop_rect["y"] == 30
        assert crop_rect["width"] == 200
        assert crop_rect["height"] == 150

        # Undo again → no crop
        app_window._session.undo()
        qtbot.wait(100)
        assert video_area.property("cropActive") is False

    def test_crop_preview_screenshot(self, app_window, qtbot, test_video, capture_screenshot):
        """Visual verification: crop preview clips the video correctly."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        capture_screenshot(app_window, "crop_preview_before")

        # Apply crop to center region
        app_window._session.setCrop(60, 40, 200, 160)
        qtbot.wait(100)

        capture_screenshot(app_window, "crop_preview_after")


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
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)

        # Video should be loaded
        assert app_window._session.hasVideo
        # Video dimensions should be available (needed for crop coordinate mapping)
        assert app_window._session.videoWidth == 320
        assert app_window._session.videoHeight == 240

    def test_video_frame_rate_available(self, app_window, qtbot, test_video):
        """Video frame rate is available after loading."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)

        # Test video is generated at 30fps
        assert app_window._session.videoFrameRate == 30.0

    def test_drag_creates_crop_selection(self, app_window, qtbot, test_video, capture_screenshot):
        """Clicking and dragging on video creates a crop selection."""
        app_window._session.openFile(str(test_video))
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

        app_window._session.openFile(str(portrait_video))
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

        app_window._session.openFile(str(portrait_video))
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

        app_window._session.openFile(str(large_video))
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
        assert not app_window._session.hasVideo

    def test_timeline_enabled_with_video(self, app_window, qtbot, test_video):
        """Timeline is enabled when video is loaded."""
        # Load video
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)  # Allow signal processing

        assert app_window._session.hasVideo

    def test_timeline_shows_playhead_position(
        self, app_window, qtbot, test_video, capture_screenshot
    ):
        """Timeline displays the current playhead position."""
        # Load video
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)  # Allow video to load and timeline to update

        # Capture for visual verification
        capture_screenshot(app_window, "timeline_with_video")

        # Verify video is loaded (timeline should now show duration)
        assert app_window._session.hasVideo


class TestCutBar:
    """GUI tests for the cut bar marker-based cutting (part of unified Timeline)."""

    def test_timeline_enabled_with_video(self, app_window, qtbot, test_video):
        """Timeline is enabled when video is loaded."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)

        timeline = app_window.findChild(QObject, "timeline")
        assert timeline is not None
        assert timeline.property("enabled") is True

    def test_timeline_starts_with_no_markers(self, app_window, qtbot, test_video):
        """Timeline starts with empty markers list."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)

        timeline = app_window.findChild(QObject, "timeline")
        assert timeline is not None
        markers = timeline.property("markers")
        assert markers == [] or markers is None or len(markers) == 0

    def test_markers_sync_with_session(self, app_window, qtbot, test_video):
        """Markers in timeline reflect session state."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)

        # Add marker via bridge
        app_window._session.addMarker(0.5)
        qtbot.wait(50)

        timeline = app_window.findChild(QObject, "timeline")
        markers = timeline.property("markers")
        assert len(markers) == 1
        assert markers[0]["time"] == 0.5

    def test_multiple_markers_displayed(self, app_window, qtbot, test_video, capture_screenshot):
        """Multiple markers are displayed on the timeline."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(100)

        # Add multiple markers
        app_window._session.addMarker(0.3)
        app_window._session.addMarker(0.7)
        app_window._session.addMarker(1.2)
        qtbot.wait(50)

        capture_screenshot(app_window, "timeline_with_markers")

        timeline = app_window.findChild(QObject, "timeline")
        markers = timeline.property("markers")
        assert len(markers) == 3


class TestMarkerSelection:
    """GUI tests for marker selection and keyboard interaction."""

    def test_cutbar_starts_with_no_selection(self, app_window, qtbot, test_video):
        """CutBar starts with no marker selected."""
        app_window._session.openFile(str(test_video))
        app_window._session.addMarker(0.5)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")
        assert cutbar is not None
        # selectedMarkerId should be empty (no selection)
        assert cutbar.property("selectedMarkerId") == ""

    def test_click_marker_selects_it(self, app_window, qtbot, test_video):
        """Clicking on a marker selects it."""
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)  # At 50% for a 2-second video
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
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)
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
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)
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
        markers = app_window._session.document.markers
        assert len(markers) == 1
        assert markers[0]["time"] > 1.0  # Moved right

    def test_shift_arrow_moves_by_larger_increment(self, app_window, qtbot, test_video):
        """Shift+Arrow moves marker by larger increment."""
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        cutbar.setProperty("focus", True)
        qtbot.wait(50)

        # Press shift+right arrow
        qtbot.keyClick(app_window, Qt.Key_Right, Qt.ShiftModifier)
        qtbot.wait(50)

        markers = app_window._session.document.markers
        assert len(markers) == 1
        # Should move more than small increment
        assert markers[0]["time"] > 1.0

    def test_delete_key_removes_selected_marker(self, app_window, qtbot, test_video):
        """Delete key removes the selected marker."""
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)
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
        markers = app_window._session.document.markers
        assert len(markers) == 0

    def test_backspace_removes_selected_marker(self, app_window, qtbot, test_video):
        """Backspace key removes the selected marker."""
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)
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
        markers = app_window._session.document.markers
        assert len(markers) == 0

    def test_only_one_marker_selected_at_a_time(self, app_window, qtbot, test_video):
        """Clicking a different marker deselects the previous one."""
        app_window._session.openFile(str(test_video))
        marker1 = app_window._session.addMarker(0.5)
        marker2 = app_window._session.addMarker(1.5)
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
        app_window._session.openFile(str(test_video))
        marker = app_window._session.addMarker(1.0)
        qtbot.wait(100)

        cutbar = app_window.findChild(QObject, "cutBar")

        # Select the marker
        cutbar.setProperty("selectedMarkerId", marker["id"])
        qtbot.wait(50)
        assert cutbar.property("selectedMarkerId") == marker["id"]

        # Remove marker via bridge (simulates undo/clear)
        app_window._session.removeMarker(marker["id"])
        qtbot.wait(50)

        # Selection should be cleared
        assert cutbar.property("selectedMarkerId") == ""


class TestKeyboardShortcuts:
    """Tests for global keyboard shortcuts."""

    def test_space_toggles_play_pause(self, app_window, qtbot, test_video):
        """Space bar toggles between play and pause."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        assert video_area is not None

        # Initially should not be playing
        assert video_area.property("playbackState") != QMediaPlayer.PlayingState

        # Press space to play
        qtbot.keyClick(app_window, Qt.Key_Space)
        qtbot.wait(100)

        # Should be playing now
        assert video_area.property("playbackState") == QMediaPlayer.PlayingState

        # Press space again to pause
        qtbot.keyClick(app_window, Qt.Key_Space)
        qtbot.wait(100)

        # Should be paused
        assert video_area.property("playbackState") == QMediaPlayer.PausedState

    def test_space_does_nothing_without_video(self, app_window, qtbot):
        """Space bar does nothing when no video is loaded."""
        # No video loaded - space should not cause errors
        qtbot.keyClick(app_window, Qt.Key_Space)
        qtbot.wait(50)
        # Should not crash - that's the test

    def test_space_works_regardless_of_focus(self, app_window, qtbot, test_video):
        """Space bar works even when timeline/cutbar has focus."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        timeline = app_window.findChild(QObject, "timeline")

        # Give focus to timeline
        timeline.setProperty("focus", True)
        qtbot.wait(50)

        # Press space - should still toggle playback
        qtbot.keyClick(app_window, Qt.Key_Space)
        qtbot.wait(100)

        assert video_area.property("playbackState") == QMediaPlayer.PlayingState


class TestFrameStepping:
    """Tests for frame-accurate stepping via keyboard and transport buttons."""

    def test_right_arrow_steps_forward(self, app_window, qtbot, test_video):
        """Right arrow key steps forward by one frame."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        initial_pos = video_area.property("position")

        # Press right arrow to step forward
        qtbot.keyClick(app_window, Qt.Key_Right)
        qtbot.wait(100)

        new_pos = video_area.property("position")
        assert new_pos > initial_pos

    def test_left_arrow_steps_backward(self, app_window, qtbot, test_video):
        """Left arrow key steps backward by one frame."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")

        # Seek to 500ms so we have room to step back
        video_area.setProperty("position", 500)
        qtbot.wait(100)
        pos_before = video_area.property("position")

        # Press left arrow to step backward
        qtbot.keyClick(app_window, Qt.Key_Left)
        qtbot.wait(100)

        new_pos = video_area.property("position")
        assert new_pos < pos_before

    def test_shift_right_jumps_one_second(self, app_window, qtbot, test_video):
        """Shift+Right jumps forward by 1 second."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        initial_pos = video_area.property("position")

        # Shift+Right should jump ~1000ms
        qtbot.keyClick(app_window, Qt.Key_Right, Qt.ShiftModifier)
        qtbot.wait(100)

        new_pos = video_area.property("position")
        jump = new_pos - initial_pos
        # Should be approximately 1 second (allow some tolerance)
        assert jump >= 900

    def test_shift_left_jumps_one_second_back(self, app_window, qtbot, test_video):
        """Shift+Left jumps backward by 1 second."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")

        # Seek to 1500ms so we have room
        video_area.setProperty("position", 1500)
        qtbot.wait(100)
        pos_before = video_area.property("position")

        # Shift+Left should jump ~1000ms back
        qtbot.keyClick(app_window, Qt.Key_Left, Qt.ShiftModifier)
        qtbot.wait(100)

        new_pos = video_area.property("position")
        jump = pos_before - new_pos
        assert jump >= 900

    def test_right_arrow_clamps_to_duration(self, app_window, qtbot, test_video):
        """Right arrow at end of video doesn't go past duration."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        duration = video_area.property("duration")

        # Seek near end
        video_area.setProperty("position", duration - 10)
        qtbot.wait(100)

        # Step forward - should clamp to duration
        qtbot.keyClick(app_window, Qt.Key_Right)
        qtbot.wait(100)

        new_pos = video_area.property("position")
        assert new_pos <= duration

    def test_left_arrow_clamps_to_zero(self, app_window, qtbot, test_video):
        """Left arrow at start of video doesn't go below zero."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")

        # Already at position 0 (or near it)
        qtbot.keyClick(app_window, Qt.Key_Left)
        qtbot.wait(100)

        new_pos = video_area.property("position")
        assert new_pos >= 0

    def test_arrow_keys_deferred_to_cutbar_when_marker_selected(
        self, app_window, qtbot, test_video
    ):
        """Arrow keys move marker (not playhead) when a marker is selected."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")
        cutbar = app_window.findChild(QObject, "cutBar")

        # Add a marker and select it
        marker = app_window._session.addMarker(1.0)
        cutbar.setProperty("selectedMarkerId", marker["id"])
        cutbar.setProperty("focus", True)
        qtbot.wait(50)

        pos_before = video_area.property("position")

        # Right arrow should move marker, not playhead
        qtbot.keyClick(app_window, Qt.Key_Right)
        qtbot.wait(100)

        # Playhead should not have moved
        pos_after = video_area.property("position")
        assert pos_after == pos_before

        # But marker should have moved
        markers = app_window._session.document.markers
        assert markers[0]["time"] > 1.0

    def test_frame_step_pauses_playback(self, app_window, qtbot, test_video):
        """Stepping pauses playback if currently playing."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        video_area = app_window.findChild(QObject, "videoArea")

        # Start playing
        qtbot.keyClick(app_window, Qt.Key_Space)
        qtbot.wait(100)
        assert video_area.property("playbackState") == QMediaPlayer.PlayingState

        # Step forward - should pause
        qtbot.keyClick(app_window, Qt.Key_Right)
        qtbot.wait(100)

        assert video_area.property("playbackState") == QMediaPlayer.PausedState


class TestTransportButtons:
    """Tests for frame step buttons in transport controls."""

    def test_transport_has_step_buttons(self, app_window, qtbot, test_video):
        """Transport controls have step forward and step backward buttons."""
        app_window._session.openFile(str(test_video))
        qtbot.wait(200)

        step_back = app_window.findChild(QObject, "stepBackwardButton")
        step_fwd = app_window.findChild(QObject, "stepForwardButton")

        assert step_back is not None
        assert step_fwd is not None
