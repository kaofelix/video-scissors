"""Tests for the EditorSession QML-facing API.

These tests verify the session's properties, slots, and signal behavior
as seen from QML. The session is now the direct QML interface (no bridge).
"""

from pathlib import Path

from conftest import generate_test_video
from video_scissors.bootstrap import create_session
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


def make_session(
    thumbnail_extractor: FakeThumbnailExtractor | None = None,
    edit_service: FakeEditService | None = None,
) -> EditorSession:
    """Create an EditorSession with simple test doubles by default."""
    return EditorSession(
        thumbnail_extractor=thumbnail_extractor or FakeThumbnailExtractor([]),
        edit_service=edit_service or FakeEditService(),
    )


class TestSessionProperties:
    """Tests for EditorSession - the QML-facing API."""

    def test_has_video_property(self):
        """Session exposes hasVideo property."""
        session = make_session()
        assert session.hasVideo is False

    def test_working_video_url(self, test_video: Path):
        """Session exposes workingVideoUrl for QML."""
        session = make_session()
        session.load(test_video)

        assert session.workingVideoUrl.startswith("file://")
        assert str(test_video) in session.workingVideoUrl

    def test_empty_url_when_no_video(self):
        """Session returns empty string when no video loaded."""
        session = make_session()
        assert session.workingVideoUrl == ""

    def test_open_file_loads_video(self, test_video: Path):
        """openFile loads the video into the session."""
        session = make_session()
        session.openFile(str(test_video))

        assert session.hasVideo is True
        assert session.source_video == test_video

    def test_open_file_emits_signals(self, test_video: Path):
        """openFile emits per-property changed signals."""
        session = make_session()

        signals = []
        session.hasVideoChanged.connect(lambda: signals.append("hasVideo"))
        session.workingVideoUrlChanged.connect(lambda: signals.append("url"))

        session.openFile(str(test_video))

        assert "hasVideo" in signals
        assert "url" in signals

    def test_close_clears_session(self, test_video: Path):
        """close clears the session."""
        session = make_session()
        session.load(test_video)

        session.close()

        assert session.hasVideo is False

    def test_reload_updates_working_video(self, test_video: Path, tmp_path: Path):
        """Setting a new working video updates workingVideoUrl."""
        session = make_session()
        session.load(test_video)

        new_video = tmp_path / "edited.mp4"
        generate_test_video(new_video, duration=1.0)

        session.set_working_video(new_video)

        assert str(new_video) in session.workingVideoUrl
        assert session.source_video == test_video


class TestSessionUndoRedo:
    """Tests for undo/redo operations via session."""

    def test_can_undo_exposed(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        assert session.canUndo is False

    def test_can_redo_exposed(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        assert session.canRedo is False

    def test_undo_restores_previous_video(self, test_video: Path, tmp_path: Path):
        session = make_session()
        session.load(test_video)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        session.set_working_video(edited)

        session.undo()

        assert str(test_video) in session.workingVideoUrl

    def test_redo_restores_undone_video(self, test_video: Path, tmp_path: Path):
        session = make_session()
        session.load(test_video)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        session.set_working_video(edited)
        session.undo()

        session.redo()

        assert str(edited) in session.workingVideoUrl

    def test_undo_emits_url_changed(self, test_video: Path, tmp_path: Path):
        session = make_session()
        session.load(test_video)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        session.set_working_video(edited)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))
        session.undo()

        assert len(signals) == 1


class TestSessionCrop:
    """Tests for crop operation via session."""

    def test_apply_crop_changes_working_video(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        session.applyCrop(0, 0, 160, 120)

        assert session.working_video != test_video
        assert session.working_video is not None
        assert session.working_video.exists()

    def test_apply_crop_emits_url_changed(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))
        session.applyCrop(0, 0, 160, 120)

        assert len(signals) == 1

    def test_crop_can_be_undone(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        session.applyCrop(0, 0, 160, 120)

        assert session.canUndo is True
        session.undo()
        assert str(test_video) in session.workingVideoUrl


class TestSessionCut:
    """Tests for cut (segment removal) operation via session."""

    def test_apply_cut_changes_working_video(self, test_video: Path):
        """applyCut creates a new working video with the segment removed."""
        session = create_session()
        session.load(test_video)

        session.applyCut(0.5, 1.0)

        assert session.working_video != test_video
        assert session.working_video is not None
        assert session.working_video.exists()

    def test_apply_cut_emits_url_changed(self, test_video: Path):
        """applyCut emits workingVideoUrlChanged signal."""
        session = create_session()
        session.load(test_video)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))
        session.applyCut(0.5, 1.0)

        assert len(signals) == 1

    def test_cut_can_be_undone(self, test_video: Path):
        """Cut operation can be undone to restore original video."""
        session = create_session()
        session.load(test_video)

        session.applyCut(0.5, 1.0)

        assert session.canUndo is True
        session.undo()
        assert str(test_video) in session.workingVideoUrl


class TestContentRevision:
    """Tests for content revision tracking (thumbnails staleness)."""

    def test_content_revision_starts_at_zero(self):
        """Content revision starts at 0 before any video is loaded."""
        session = make_session()
        assert session.contentRevision == 0

    def test_content_revision_increments_on_file_open(self, test_video: Path):
        """Opening a file increments the content revision."""
        session = make_session()
        session.openFile(str(test_video))
        assert session.contentRevision > 0

    def test_content_revision_increments_on_edit_spec_change(self, test_video: Path):
        """Edit spec changes (crop, cut) increment the content revision."""
        session = make_session()
        session.load(test_video)
        rev_after_load = session.contentRevision

        session.setCrop(10, 20, 100, 80)

        assert session.contentRevision > rev_after_load

    def test_content_revision_increments_on_close(self, test_video: Path):
        """Closing the session increments the content revision."""
        session = make_session()
        session.load(test_video)
        rev_after_load = session.contentRevision

        session.close()

        assert session.contentRevision > rev_after_load

    def test_display_dimensions_update_on_file_open(self, test_video: Path):
        """displayWidth/displayHeight reflect video dimensions after file open."""
        session = make_session()

        assert session.displayWidth == 0
        assert session.displayHeight == 0

        session.openFile(str(test_video))  # 320x240

        assert session.displayWidth == 320
        assert session.displayHeight == 240

    def test_request_thumbnails_ignores_stale_revision(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        session = make_session(thumbnail_extractor=extractor)
        session.load(test_video)

        signals = []
        session.thumbnailsReady.connect(lambda urls: signals.append(urls))

        stale_revision = session.contentRevision - 1
        session.requestThumbnails(3, 40, stale_revision)
        qtbot.wait(50)

        assert signals == []
        assert extractor.calls == []

    def test_request_thumbnails_emits_for_current_revision(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        session = make_session(thumbnail_extractor=extractor)
        session.load(test_video)

        signals = []
        session.thumbnailsReady.connect(lambda urls: signals.append(urls))

        session.requestThumbnails(3, 40, session.contentRevision)
        qtbot.waitUntil(lambda: len(signals) == 1, timeout=1000)

        assert signals == [[f"file://{fake_frame}"]]
        assert extractor.calls == [(test_video, 3, 40, None)]

    def test_request_thumbnails_passes_crop_from_edit_spec(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        """Thumbnail request passes the current crop to the extractor."""
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        session = make_session(thumbnail_extractor=extractor)
        session.load(test_video)
        session.setCrop(40, 30, 200, 150)

        signals = []
        session.thumbnailsReady.connect(lambda urls: signals.append(urls))

        session.requestThumbnails(3, 40, session.contentRevision)
        qtbot.waitUntil(lambda: len(signals) == 1, timeout=1000)

        expected_crop = CropRect(x=40, y=30, width=200, height=150)
        assert extractor.calls == [(test_video, 3, 40, expected_crop)]


class TestSessionMarkers:
    """Tests for cut marker operations via session."""

    def test_markers_exposed_via_document(self, test_video: Path):
        """Session exposes markers through document model."""
        session = make_session()
        session.load(test_video)
        assert session.document.markers == []

    def test_add_marker_returns_marker_object(self, test_video: Path):
        """addMarker returns the created marker with id and time."""
        session = make_session()
        session.load(test_video)

        result = session.addMarker(1.5)

        assert result is not None
        assert "id" in result
        assert result["time"] == 1.5
        assert len(result["id"]) == 32

    def test_add_marker_adds_to_list(self, test_video: Path):
        """addMarker adds a marker object to the document."""
        session = make_session()
        session.load(test_video)

        session.addMarker(1.5)

        assert len(session.document.markers) == 1
        assert session.document.markers[0]["time"] == 1.5

    def test_remove_marker_by_id(self, test_video: Path):
        """removeMarker removes the marker by its ID."""
        session = make_session()
        session.load(test_video)
        marker1 = session.addMarker(1.0)
        session.addMarker(2.0)

        session.removeMarker(marker1["id"])

        assert marker_times(session.document.markers) == [2.0]

    def test_clear_markers_removes_all(self, test_video: Path):
        """clearMarkers removes all markers."""
        session = make_session()
        session.load(test_video)
        session.addMarker(1.0)
        session.addMarker(2.0)

        session.clearMarkers()

        assert session.document.markers == []

    def test_move_marker_by_id(self, test_video: Path):
        """moveMarker updates marker time by ID."""
        session = make_session()
        session.load(test_video)
        marker = session.addMarker(1.0)

        session.moveMarker(marker["id"], 2.0)

        assert len(session.document.markers) == 1
        assert session.document.markers[0]["id"] == marker["id"]
        assert session.document.markers[0]["time"] == 2.0

    def test_add_marker_emits_markers_changed(self, test_video: Path):
        """addMarker emits markersChanged signal on document model."""
        session = make_session()
        session.load(test_video)

        signals = []
        session.document.markersChanged.connect(lambda: signals.append(True))

        session.addMarker(1.5)

        assert len(signals) == 1

    def test_marker_undo_emits_markers_changed(self, test_video: Path):
        """Undoing a marker operation emits markersChanged."""
        session = make_session()
        session.load(test_video)
        session.addMarker(1.5)

        signals = []
        session.document.markersChanged.connect(lambda: signals.append(True))

        session.undo()

        assert len(signals) == 1

    def test_cut_adjusts_markers(self, test_video: Path):
        """Cutting a segment adjusts marker positions."""
        session = create_session()
        session.load(test_video)

        session.addMarker(0.3)  # Before cut
        session.addMarker(0.7)  # Inside cut [0.5, 1.0]
        session.addMarker(1.5)  # After cut

        session.applyCut(0.5, 1.0)

        times = marker_times(session.document.markers)
        assert 0.3 in times  # Before - unchanged
        assert 0.7 not in times  # Inside - removed
        assert 1.0 in times  # 1.5 shifted by 0.5

    def test_cut_emits_markers_changed_when_adjusted(self, test_video: Path):
        """Cutting emits markersChanged when markers are adjusted."""
        session = create_session()
        session.load(test_video)
        session.addMarker(1.5)

        signals = []
        session.document.markersChanged.connect(lambda: signals.append(True))

        session.applyCut(0.5, 1.0)

        assert len(signals) == 1


class TestSuggestedPosition:
    """Tests for playhead position stability across operations."""

    def test_suggested_position_defaults_to_zero(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        assert session.suggestedPositionMs == 0

    def test_apply_crop_preserves_position(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        session.applyCrop(0, 0, 160, 120, 1500)

        assert session.suggestedPositionMs == 1500

    def test_apply_cut_position_before_cut_unchanged(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        session.applyCut(0.5, 1.0, 300)

        assert session.suggestedPositionMs == 300

    def test_apply_cut_position_inside_cut_snaps_to_start(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        session.applyCut(0.5, 1.0, 700)

        assert session.suggestedPositionMs == 500

    def test_apply_cut_position_after_cut_shifted(self, test_video: Path):
        session = create_session()
        session.load(test_video)

        session.applyCut(0.5, 1.0, 1500)

        assert session.suggestedPositionMs == 1000

    def test_undo_preserves_position(self, test_video: Path, tmp_path: Path):
        session = make_session()
        session.load(test_video)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        session.set_working_video(edited)

        session.undo(750)

        assert session.suggestedPositionMs == 750

    def test_redo_preserves_position(self, test_video: Path, tmp_path: Path):
        session = make_session()
        session.load(test_video)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        session.set_working_video(edited)
        session.undo(0)

        session.redo(500)

        assert session.suggestedPositionMs == 500


class TestUndoStateSignal:
    """Tests for proper undo state signaling via QUndoStack connection."""

    def test_undo_state_changed_signal_exists(self, test_video: Path):
        session = make_session()
        signals = []
        session.undoStateChanged.connect(lambda: signals.append(True))

    def test_add_marker_emits_undo_state_changed(self, test_video: Path):
        session = make_session()
        session.load(test_video)

        signals = []
        session.undoStateChanged.connect(lambda: signals.append(True))

        session.addMarker(1.5)

        assert len(signals) >= 1

    def test_add_cut_emits_undo_state_changed(self, test_video: Path):
        session = make_session()
        session.load(test_video)

        signals = []
        session.undoStateChanged.connect(lambda: signals.append(True))

        session.addCut(1.0, 2.0)

        assert len(signals) >= 1

    def test_add_cut_does_not_emit_url_changed(self, test_video: Path):
        """addCut should not emit workingVideoUrlChanged."""
        session = make_session()
        session.load(test_video)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))

        session.addCut(1.0, 2.0)

        assert len(signals) == 0

    def test_set_crop_does_not_emit_url_changed(self, test_video: Path):
        """setCrop should not emit workingVideoUrlChanged."""
        session = make_session()
        session.load(test_video)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))

        session.setCrop(10, 20, 100, 80)

        assert len(signals) == 0

    def test_undo_marker_does_not_emit_url_changed(self, test_video: Path):
        """Undoing a marker-only operation should not emit workingVideoUrlChanged."""
        session = make_session()
        session.load(test_video)
        session.addMarker(1.5)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))

        session.undo()

        assert len(signals) == 0

    def test_undo_video_change_emits_url_changed(self, test_video: Path, tmp_path: Path):
        """Undoing a video change should emit workingVideoUrlChanged."""
        session = make_session()
        session.load(test_video)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        session.set_working_video(edited)

        signals = []
        session.workingVideoUrlChanged.connect(lambda: signals.append(True))

        session.undo()

        assert len(signals) == 1


class TestEditSpecProperties:
    """Tests for non-destructive EditSpec operations via session."""

    def test_add_cut_updates_cut_regions(self, test_video: Path):
        """addCut slot adds cut to EditSpec and exposes via document.editSpec."""
        session = make_session()
        session.load(test_video)

        session.addCut(1.0, 2.0)

        regions = session.document.editSpec.cutRegions
        assert len(regions) == 1
        assert regions[0]["start"] == 1000
        assert regions[0]["end"] == 2000

    def test_add_cut_emits_cuts_changed(self, test_video: Path, qtbot):
        """addCut emits cutsChanged signal on EditSpecModel."""
        session = make_session()
        session.load(test_video)

        with qtbot.waitSignal(session.document.editSpec.cutsChanged, timeout=100):
            session.addCut(1.0, 2.0)

    def test_set_crop_updates_crop_rect(self, test_video: Path):
        """setCrop slot sets crop and exposes via document.editSpec."""
        session = make_session()
        session.load(test_video)

        session.setCrop(10, 20, 100, 80)

        crop = session.document.editSpec.cropRect
        assert crop["x"] == 10
        assert crop["y"] == 20
        assert crop["width"] == 100
        assert crop["height"] == 80

    def test_set_crop_emits_crop_changed(self, test_video: Path, qtbot):
        """setCrop emits cropChanged signal on EditSpecModel."""
        session = make_session()
        session.load(test_video)

        with qtbot.waitSignal(session.document.editSpec.cropChanged, timeout=100):
            session.setCrop(10, 20, 100, 80)

    def test_effective_duration_reflects_cuts(self, test_video: Path):
        """effectiveDurationMs accounts for cuts."""
        session = make_session()
        session.load(test_video)  # 2 second video

        session.addCut(0.5, 1.0)

        assert session.effectiveDurationMs == 1500

    def test_source_to_effective_conversion(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        session.addCut(0.5, 1.0)

        assert session.sourceToEffective(1500) == 1000

    def test_effective_to_source_conversion(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        session.addCut(0.5, 1.0)

        assert session.effectiveToSource(750) == 1250

    def test_crop_rect_none_when_no_crop(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        assert session.document.editSpec.cropRect is None

    def test_cut_regions_empty_when_no_cuts(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        assert session.document.editSpec.cutRegions == []

    def test_has_cuts_property(self, test_video: Path):
        session = make_session()
        session.load(test_video)

        assert session.document.editSpec.hasCuts is False
        session.addCut(1.0, 2.0)
        assert session.document.editSpec.hasCuts is True

    def test_has_crop_property(self, test_video: Path):
        session = make_session()
        session.load(test_video)

        assert session.document.editSpec.hasCrop is False
        session.setCrop(10, 20, 100, 80)
        assert session.document.editSpec.hasCrop is True

    def test_display_dimensions_match_source_when_no_crop(self, test_video: Path):
        session = make_session()
        session.load(test_video)  # 320x240

        assert session.displayWidth == 320
        assert session.displayHeight == 240

    def test_display_dimensions_match_crop_when_cropped(self, test_video: Path):
        session = make_session()
        session.load(test_video)

        session.setCrop(40, 30, 200, 150)

        assert session.displayWidth == 200
        assert session.displayHeight == 150

    def test_display_dimensions_revert_on_undo(self, test_video: Path):
        session = make_session()
        session.load(test_video)

        session.setCrop(40, 30, 200, 150)
        session.undo()

        assert session.displayWidth == 320
        assert session.displayHeight == 240

    def test_undo_emits_cuts_changed(self, test_video: Path, qtbot):
        """Undo emits cutsChanged when edit spec changes."""
        session = make_session()
        session.load(test_video)
        session.addCut(1.0, 2.0)

        with qtbot.waitSignal(session.document.editSpec.cutsChanged, timeout=100):
            session.undo(0)

    def test_redo_emits_cuts_changed(self, test_video: Path, qtbot):
        """Redo emits cutsChanged when edit spec changes."""
        session = make_session()
        session.load(test_video)
        session.addCut(1.0, 2.0)
        session.undo(0)

        with qtbot.waitSignal(session.document.editSpec.cutsChanged, timeout=100):
            session.redo(0)


def marker_times(markers: list) -> list[float]:
    """Extract times from marker objects."""
    return [m["time"] for m in markers]
