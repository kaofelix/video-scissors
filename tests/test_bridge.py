"""Tests for the QML/Python bridge."""

import tempfile
from pathlib import Path

from conftest import generate_test_video
from video_scissors.bootstrap import create_session_bridge
from video_scissors.bridge import SessionBridge
from video_scissors.document import CropRect
from video_scissors.services import EditResult
from video_scissors.session import EditorSession


class FakeThumbnailExtractor:
    """Test double for thumbnail extraction."""

    def __init__(self, frames: list[Path]):
        self.frames = frames
        self.calls: list[tuple] = []

    def extract(
        self,
        video_path: Path,
        frame_count: int,
        thumb_height: int,
        crop: CropRect | None = None,
    ) -> list[Path]:
        self.calls.append((video_path, frame_count, thumb_height, crop))
        return self.frames


class FakeEditService:
    """Test double for edit application."""

    def __init__(self, output_path: Path | None = None):
        self.output_path = output_path or Path("/tmp/fake-edit.mp4")

    def apply_crop(self, source: Path, request) -> EditResult:
        return EditResult(output_path=self.output_path)

    def apply_cut(self, source: Path, request) -> EditResult:
        return EditResult(output_path=self.output_path)


def make_bridge(
    session: EditorSession,
    thumbnail_extractor: FakeThumbnailExtractor | None = None,
    edit_service: FakeEditService | None = None,
) -> SessionBridge:
    """Create a SessionBridge with simple test doubles by default."""
    return SessionBridge(
        session,
        thumbnail_extractor=thumbnail_extractor or FakeThumbnailExtractor([]),
        edit_service=edit_service or FakeEditService(),
    )


class TestSessionBridge:
    """Tests for SessionBridge - the QML-facing API."""

    def test_bridge_exposes_has_video(self):
        """Bridge exposes hasVideo property."""
        session = EditorSession()
        bridge = make_bridge(session)

        assert bridge.hasVideo is False

    def test_bridge_exposes_working_video_path(self, test_video: Path):
        """Bridge exposes workingVideoUrl for QML."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.workingVideoUrl.startswith("file://")
        assert str(test_video) in bridge.workingVideoUrl

    def test_bridge_returns_empty_url_when_no_video(self):
        """Bridge returns empty string when no video loaded."""
        session = EditorSession()
        bridge = make_bridge(session)

        assert bridge.workingVideoUrl == ""

    def test_open_file_loads_into_session(self, test_video: Path):
        """openFile loads the video into the session."""
        session = EditorSession()
        bridge = make_bridge(session)

        bridge.openFile(str(test_video))

        assert session.has_video is True
        assert session.source_video == test_video

    def test_open_file_emits_video_changed_signal(self, test_video: Path):
        """openFile emits videoChanged signal."""
        session = EditorSession()
        bridge = make_bridge(session)

        signal_received = []
        bridge.videoChanged.connect(lambda: signal_received.append(True))

        bridge.openFile(str(test_video))

        assert len(signal_received) == 1

    def test_close_clears_session(self, test_video: Path):
        """close clears the session."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.close()

        assert session.has_video is False

    def test_reload_updates_working_video(self, test_video: Path, tmp_path: Path):
        """Reloading with new path updates workingVideoUrl."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        new_video = tmp_path / "edited.mp4"
        generate_test_video(new_video, duration=1.0)

        bridge.setWorkingVideo(str(new_video))

        assert str(new_video) in bridge.workingVideoUrl
        assert session.source_video == test_video


class TestBridgeUndoRedo:
    """Tests for undo/redo operations via bridge."""

    def test_can_undo_exposed(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.canUndo is False

    def test_can_redo_exposed(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.canRedo is False

    def test_undo_restores_previous_video(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        bridge.undo()

        assert str(test_video) in bridge.workingVideoUrl

    def test_redo_restores_undone_video(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))
        bridge.undo()

        bridge.redo()

        assert str(edited) in bridge.workingVideoUrl

    def test_undo_emits_video_changed(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        signals = []
        bridge.videoChanged.connect(lambda: signals.append(True))
        bridge.undo()

        assert len(signals) == 1


class TestBridgeCrop:
    """Tests for crop operation via bridge."""

    def test_apply_crop_changes_working_video(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCrop(0, 0, 160, 120)

            assert session.working_video != test_video
            assert session.working_video is not None
            assert session.working_video.exists()

    def test_apply_crop_emits_video_changed(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            signals = []
            bridge.videoChanged.connect(lambda: signals.append(True))
            bridge.applyCrop(0, 0, 160, 120)

            assert len(signals) == 1

    def test_crop_can_be_undone(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCrop(0, 0, 160, 120)

            assert bridge.canUndo is True
            bridge.undo()
            assert str(test_video) in bridge.workingVideoUrl


class TestBridgeCut:
    """Tests for cut (segment removal) operation via bridge."""

    def test_apply_cut_changes_working_video(self, test_video: Path):
        """applyCut creates a new working video with the segment removed."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCut(0.5, 1.0)  # Remove 0.5 seconds

            assert session.working_video != test_video
            assert session.working_video is not None
            assert session.working_video.exists()

    def test_apply_cut_emits_video_changed(self, test_video: Path):
        """applyCut emits videoChanged signal."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            signals = []
            bridge.videoChanged.connect(lambda: signals.append(True))
            bridge.applyCut(0.5, 1.0)

            assert len(signals) == 1

    def test_cut_can_be_undone(self, test_video: Path):
        """Cut operation can be undone to restore original video."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCut(0.5, 1.0)

            assert bridge.canUndo is True
            bridge.undo()
            assert str(test_video) in bridge.workingVideoUrl


class TestBridgeContentRevision:
    """Tests for content revision tracking (thumbnails staleness)."""

    def test_content_revision_starts_at_zero(self):
        """Content revision starts at 0 before any video is loaded."""
        session = EditorSession()
        bridge = make_bridge(session)

        assert bridge.contentRevision == 0

    def test_content_revision_increments_on_file_open(self, test_video: Path):
        """Opening a file increments the content revision."""
        session = EditorSession()
        bridge = make_bridge(session)

        bridge.openFile(str(test_video))

        assert bridge.contentRevision > 0

    def test_content_revision_increments_on_edit_spec_change(self, test_video: Path):
        """Edit spec changes (crop, cut) increment the content revision."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        rev_after_load = bridge.contentRevision

        bridge.setCrop(10, 20, 100, 80)

        assert bridge.contentRevision > rev_after_load

    def test_content_revision_increments_on_close(self, test_video: Path):
        """Closing the session increments the content revision."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        rev_after_load = bridge.contentRevision

        bridge.close()

        assert bridge.contentRevision > rev_after_load

    def test_display_dimensions_update_on_file_open(self, test_video: Path):
        """displayWidth/displayHeight reflect video dimensions after file open."""
        session = EditorSession()
        bridge = make_bridge(session)

        # Before loading: zero dimensions
        assert bridge.displayWidth == 0
        assert bridge.displayHeight == 0

        bridge.openFile(str(test_video))  # 320x240

        assert bridge.displayWidth == 320
        assert bridge.displayHeight == 240

    def test_request_thumbnails_ignores_stale_revision(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        session = EditorSession()
        session.load(test_video)
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        bridge = make_bridge(session, thumbnail_extractor=extractor)

        signals = []
        bridge.thumbnailsReady.connect(lambda urls: signals.append(urls))

        stale_revision = bridge.contentRevision - 1
        bridge.requestThumbnails(3, 40, stale_revision)
        qtbot.wait(50)

        assert signals == []
        assert extractor.calls == []

    def test_request_thumbnails_emits_for_current_revision(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        session = EditorSession()
        session.load(test_video)
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        bridge = make_bridge(session, thumbnail_extractor=extractor)

        signals = []
        bridge.thumbnailsReady.connect(lambda urls: signals.append(urls))

        bridge.requestThumbnails(3, 40, bridge.contentRevision)
        qtbot.waitUntil(lambda: len(signals) == 1, timeout=1000)

        assert signals == [[f"file://{fake_frame}"]]
        assert extractor.calls == [(test_video, 3, 40, None)]

    def test_request_thumbnails_passes_crop_from_edit_spec(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        """Thumbnail request passes the current crop to the extractor."""
        session = EditorSession()
        session.load(test_video)
        session.set_crop(40, 30, 200, 150)

        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        bridge = make_bridge(session, thumbnail_extractor=extractor)

        signals = []
        bridge.thumbnailsReady.connect(lambda urls: signals.append(urls))

        bridge.requestThumbnails(3, 40, bridge.contentRevision)
        qtbot.waitUntil(lambda: len(signals) == 1, timeout=1000)

        expected_crop = CropRect(x=40, y=30, width=200, height=150)
        assert extractor.calls == [(test_video, 3, 40, expected_crop)]


def marker_times_from_bridge(markers: list) -> list[float]:
    """Extract times from bridge marker objects."""
    return [m["time"] for m in markers]


class TestBridgeMarkers:
    """Tests for cut marker operations via bridge."""

    def test_markers_exposed_as_list_of_objects(self, test_video: Path):
        """Bridge exposes markers as a list of {id, time} objects for QML."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.markers == []

    def test_add_marker_returns_marker_object(self, test_video: Path):
        """addMarker returns the created marker with id and time."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        result = bridge.addMarker(1.5)

        assert result is not None
        assert "id" in result
        assert result["time"] == 1.5
        assert len(result["id"]) == 32

    def test_add_marker_adds_to_list(self, test_video: Path):
        """addMarker adds a marker object to the list."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.addMarker(1.5)

        assert len(bridge.markers) == 1
        assert bridge.markers[0]["time"] == 1.5

    def test_remove_marker_by_id(self, test_video: Path):
        """removeMarker removes the marker by its ID."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        marker1 = bridge.addMarker(1.0)
        bridge.addMarker(2.0)

        bridge.removeMarker(marker1["id"])

        assert marker_times_from_bridge(bridge.markers) == [2.0]

    def test_clear_markers_removes_all(self, test_video: Path):
        """clearMarkers removes all markers."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addMarker(1.0)
        bridge.addMarker(2.0)

        bridge.clearMarkers()

        assert bridge.markers == []

    def test_move_marker_by_id(self, test_video: Path):
        """moveMarker updates marker time by ID."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        marker = bridge.addMarker(1.0)

        bridge.moveMarker(marker["id"], 2.0)

        assert len(bridge.markers) == 1
        assert bridge.markers[0]["id"] == marker["id"]
        assert bridge.markers[0]["time"] == 2.0

    def test_add_marker_emits_markers_changed(self, test_video: Path):
        """addMarker emits markersChanged signal."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        signals = []
        bridge.markersChanged.connect(lambda: signals.append(True))

        bridge.addMarker(1.5)

        assert len(signals) == 1

    def test_marker_undo_emits_markers_changed(self, test_video: Path):
        """Undoing a marker operation emits markersChanged."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addMarker(1.5)

        signals = []
        bridge.markersChanged.connect(lambda: signals.append(True))

        bridge.undo()

        assert len(signals) == 1

    def test_cut_adjusts_markers(self, test_video: Path):
        """Cutting a segment adjusts marker positions."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            # Add markers
            bridge.addMarker(0.3)  # Before cut
            bridge.addMarker(0.7)  # Inside cut [0.5, 1.0]
            bridge.addMarker(1.5)  # After cut

            # Apply cut
            bridge.applyCut(0.5, 1.0)

            # Check adjusted markers
            times = marker_times_from_bridge(bridge.markers)
            assert 0.3 in times  # Before - unchanged
            assert 0.7 not in times  # Inside - removed
            assert 1.0 in times  # 1.5 shifted by 0.5

    def test_cut_emits_markers_changed_when_adjusted(self, test_video: Path):
        """Cutting emits markersChanged when markers are adjusted."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.addMarker(1.5)  # Will be adjusted

            signals = []
            bridge.markersChanged.connect(lambda: signals.append(True))

            bridge.applyCut(0.5, 1.0)

            assert len(signals) == 1


class TestBridgeSuggestedPosition:
    """Tests for playhead position stability across operations."""

    def test_suggested_position_defaults_to_zero(self, test_video: Path):
        """suggestedPositionMs defaults to 0."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.suggestedPositionMs == 0

    def test_apply_crop_preserves_position(self, test_video: Path):
        """applyCrop sets suggestedPositionMs to the passed position."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            bridge.applyCrop(0, 0, 160, 120, 1500)  # currentPositionMs=1500

            assert bridge.suggestedPositionMs == 1500

    def test_apply_cut_position_before_cut_unchanged(self, test_video: Path):
        """Position before cut region stays unchanged."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            # Position at 300ms, cut is [500ms, 1000ms]
            bridge.applyCut(0.5, 1.0, 300)

            assert bridge.suggestedPositionMs == 300

    def test_apply_cut_position_inside_cut_snaps_to_start(self, test_video: Path):
        """Position inside cut region snaps to cut start."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            # Position at 700ms, cut is [500ms, 1000ms]
            bridge.applyCut(0.5, 1.0, 700)

            assert bridge.suggestedPositionMs == 500

    def test_apply_cut_position_after_cut_shifted(self, test_video: Path):
        """Position after cut region is shifted by cut duration."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            # Position at 1500ms, cut is [500ms, 1000ms] (500ms cut)
            # New position should be 1500 - 500 = 1000ms
            bridge.applyCut(0.5, 1.0, 1500)

            assert bridge.suggestedPositionMs == 1000

    def test_undo_preserves_position(self, test_video: Path, tmp_path: Path):
        """Undo keeps position at same timestamp."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        bridge.undo(750)  # currentPositionMs=750

        assert bridge.suggestedPositionMs == 750

    def test_redo_preserves_position(self, test_video: Path, tmp_path: Path):
        """Redo keeps position at same timestamp."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))
        bridge.undo(0)

        bridge.redo(500)  # currentPositionMs=500

        assert bridge.suggestedPositionMs == 500


class TestBridgeUndoStateSignal:
    """Tests for proper undo state signaling via QUndoStack connection."""

    def test_undo_state_changed_signal_exists(self, test_video: Path):
        """Bridge has an undoStateChanged signal."""
        session = EditorSession()
        bridge = make_bridge(session)

        # Signal should exist and be connectable
        signals = []
        bridge.undoStateChanged.connect(lambda: signals.append(True))

    def test_add_marker_emits_undo_state_changed(self, test_video: Path):
        """Adding a marker emits undoStateChanged so QML updates canUndo."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        signals = []
        bridge.undoStateChanged.connect(lambda: signals.append(True))

        bridge.addMarker(1.5)

        assert len(signals) >= 1

    def test_add_cut_emits_undo_state_changed(self, test_video: Path):
        """Adding a cut emits undoStateChanged."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        signals = []
        bridge.undoStateChanged.connect(lambda: signals.append(True))

        bridge.addCut(1.0, 2.0)

        assert len(signals) >= 1

    def test_add_cut_does_not_emit_video_changed(self, test_video: Path):
        """addCut should not emit videoChanged - it doesn't change the video."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        signals = []
        bridge.videoChanged.connect(lambda: signals.append(True))

        bridge.addCut(1.0, 2.0)

        assert len(signals) == 0

    def test_set_crop_does_not_emit_video_changed(self, test_video: Path):
        """setCrop should not emit videoChanged - it doesn't change the video."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        signals = []
        bridge.videoChanged.connect(lambda: signals.append(True))

        bridge.setCrop(10, 20, 100, 80)

        assert len(signals) == 0

    def test_undo_marker_does_not_emit_video_changed(self, test_video: Path):
        """Undoing a marker-only operation should not emit videoChanged."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addMarker(1.5)

        signals = []
        bridge.videoChanged.connect(lambda: signals.append(True))

        bridge.undo()

        assert len(signals) == 0

    def test_undo_video_change_emits_video_changed(self, test_video: Path, tmp_path: Path):
        """Undoing a video change (SetWorkingVideo) should emit videoChanged."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        signals = []
        bridge.videoChanged.connect(lambda: signals.append(True))

        bridge.undo()

        assert len(signals) == 1


class TestEditSpecBridge:
    """Tests for non-destructive EditSpec operations via bridge."""

    def test_add_cut_updates_cut_regions(self, test_video: Path):
        """addCut slot adds cut to EditSpec and exposes via cutRegions."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.addCut(1.0, 2.0)

        assert len(bridge.cutRegions) == 1
        assert bridge.cutRegions[0]["start"] == 1000  # milliseconds
        assert bridge.cutRegions[0]["end"] == 2000

    def test_add_cut_emits_edit_spec_changed(self, test_video: Path, qtbot):
        """addCut emits editSpecChanged signal."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        with qtbot.waitSignal(bridge.editSpecChanged, timeout=100):
            bridge.addCut(1.0, 2.0)

    def test_set_crop_updates_crop_rect(self, test_video: Path):
        """setCrop slot sets crop and exposes via cropRect."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.setCrop(10, 20, 100, 80)

        crop = bridge.cropRect
        assert crop["x"] == 10
        assert crop["y"] == 20
        assert crop["width"] == 100
        assert crop["height"] == 80

    def test_set_crop_emits_edit_spec_changed(self, test_video: Path, qtbot):
        """setCrop emits editSpecChanged signal."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        with qtbot.waitSignal(bridge.editSpecChanged, timeout=100):
            bridge.setCrop(10, 20, 100, 80)

    def test_effective_duration_reflects_cuts(self, test_video: Path):
        """effectiveDurationMs accounts for cuts."""
        session = EditorSession()
        session.load(test_video)  # 2 second video
        bridge = make_bridge(session)

        bridge.addCut(0.5, 1.0)  # Remove 0.5 seconds

        # 2.0 - 0.5 = 1.5 seconds = 1500ms
        assert bridge.effectiveDurationMs == 1500

    def test_source_to_effective_conversion(self, test_video: Path):
        """sourceToEffective converts times correctly."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addCut(0.5, 1.0)  # Cut 0.5-1.0s (in seconds)

        # Source 1500ms (after cut) -> Effective 1000ms
        assert bridge.sourceToEffective(1500) == 1000

    def test_effective_to_source_conversion(self, test_video: Path):
        """effectiveToSource converts times correctly."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addCut(0.5, 1.0)  # Cut 0.5-1.0s (in seconds)

        # Effective 750ms -> Source 1250ms
        assert bridge.effectiveToSource(750) == 1250

    def test_crop_rect_none_when_no_crop(self, test_video: Path):
        """cropRect returns None when no crop set."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.cropRect is None

    def test_cut_regions_empty_when_no_cuts(self, test_video: Path):
        """cutRegions returns empty list when no cuts."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.cutRegions == []

    def test_has_cuts_property(self, test_video: Path):
        """hasCuts property reflects whether cuts exist."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.hasCuts is False

        bridge.addCut(1.0, 2.0)

        assert bridge.hasCuts is True

    def test_has_crop_property(self, test_video: Path):
        """hasCrop property reflects whether crop is set."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.hasCrop is False

        bridge.setCrop(10, 20, 100, 80)

        assert bridge.hasCrop is True

    def test_display_dimensions_match_source_when_no_crop(self, test_video: Path):
        """displayWidth/displayHeight return source dimensions with no crop."""
        session = EditorSession()
        session.load(test_video)  # 320x240
        bridge = make_bridge(session)

        assert bridge.displayWidth == 320
        assert bridge.displayHeight == 240

    def test_display_dimensions_match_crop_when_cropped(self, test_video: Path):
        """displayWidth/displayHeight return crop dimensions when crop is set."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.setCrop(40, 30, 200, 150)

        assert bridge.displayWidth == 200
        assert bridge.displayHeight == 150

    def test_display_dimensions_revert_on_undo(self, test_video: Path):
        """displayWidth/displayHeight revert to source on undo."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.setCrop(40, 30, 200, 150)
        bridge.undo()

        assert bridge.displayWidth == 320
        assert bridge.displayHeight == 240

    def test_undo_emits_edit_spec_changed(self, test_video: Path, qtbot):
        """Undo emits editSpecChanged when edit spec changes."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addCut(1.0, 2.0)

        with qtbot.waitSignal(bridge.editSpecChanged, timeout=100):
            bridge.undo(0)

    def test_redo_emits_edit_spec_changed(self, test_video: Path, qtbot):
        """Redo emits editSpecChanged when edit spec changes."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)
        bridge.addCut(1.0, 2.0)
        bridge.undo(0)

        with qtbot.waitSignal(bridge.editSpecChanged, timeout=100):
            bridge.redo(0)
