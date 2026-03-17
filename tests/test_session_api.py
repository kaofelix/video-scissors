"""Tests for the EditorSession QML-facing API.

These tests verify the session's properties, slots, and signal behavior
as seen from QML. The session is now the direct QML interface (no bridge).
"""

from pathlib import Path

from video_scissors.document import CropRect
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


def make_session(
    thumbnail_extractor: FakeThumbnailExtractor | None = None,
) -> EditorSession:
    """Create an EditorSession with simple test doubles by default."""
    return EditorSession(
        thumbnail_extractor=thumbnail_extractor or FakeThumbnailExtractor([]),
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


class TestSuggestedPosition:
    """Tests for playhead position stability across operations."""

    def test_suggested_position_defaults_to_zero(self, test_video: Path):
        session = make_session()
        session.load(test_video)
        assert session.suggestedPositionMs == 0


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

    def test_effective_markers_no_cuts(self, test_video: Path):
        """effectiveMarkers returns source times when no cuts exist."""
        session = make_session()
        session.load(test_video)
        session.addMarker(0.5)
        session.addMarker(1.5)

        markers: list[dict] = session.effectiveMarkers  # type: ignore[assignment]
        times = [m["time"] for m in markers]
        assert times == [0.5, 1.5]

    def test_effective_markers_with_cut(self, test_video: Path):
        """effectiveMarkers converts times to effective coordinates."""
        session = make_session()
        session.load(test_video)
        session.addMarker(0.3)  # Before cut: stays 0.3
        session.addMarker(1.5)  # After cut [0.5, 1.0): shifts by -0.5 → 1.0
        session.addCut(0.5, 1.0)

        markers: list[dict] = session.effectiveMarkers  # type: ignore[assignment]
        times = sorted(m["time"] for m in markers)
        assert times[0] == 0.3
        assert times[1] == 1.0

    def test_effective_markers_preserves_ids(self, test_video: Path):
        """effectiveMarkers preserves marker IDs for mapping back."""
        session = make_session()
        session.load(test_video)
        result = session.addMarker(1.5)
        marker_id = result["id"]

        markers = session.effectiveMarkers
        assert len(markers) == 1
        assert markers[0]["id"] == marker_id

    def test_effective_markers_signal_on_marker_change(self, test_video: Path, qtbot):
        """effectiveMarkersChanged fires when markers change."""
        session = make_session()
        session.load(test_video)

        with qtbot.waitSignal(session.effectiveMarkersChanged, timeout=100):
            session.addMarker(0.5)

    def test_effective_markers_signal_on_cut_change(self, test_video: Path, qtbot):
        """effectiveMarkersChanged fires when cuts change."""
        session = make_session()
        session.load(test_video)
        session.addMarker(1.5)

        with qtbot.waitSignal(session.effectiveMarkersChanged, timeout=100):
            session.addCut(0.5, 1.0)

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


class TestExportVideo:
    """Tests for export slot on EditorSession."""

    def test_export_calls_export_service(self, test_video: Path, tmp_path: Path):
        """exportVideo slot delegates to the export service."""
        calls: list[tuple] = []

        class FakeExportService:
            def export(self, source, edit_spec, output, on_progress=None):
                calls.append((source, edit_spec, output))

        session = make_session()
        session._export_service = FakeExportService()
        session.load(test_video)

        output = tmp_path / "out.mp4"
        session.exportVideo(str(output))

        assert len(calls) == 1
        assert calls[0][0] == test_video
        assert calls[0][2] == output

    def test_export_does_nothing_without_video(self, tmp_path: Path):
        """exportVideo does nothing when no video is loaded."""
        session = make_session()
        # Should not crash
        session.exportVideo(str(tmp_path / "out.mp4"))

    def test_export_passes_current_edit_spec(self, test_video: Path, tmp_path: Path):
        """exportVideo passes the current edit spec to the service."""
        calls: list[tuple] = []

        class FakeExportService:
            def export(self, source, edit_spec, output, on_progress=None):
                calls.append((source, edit_spec, output))

        session = make_session()
        session._export_service = FakeExportService()
        session.load(test_video)
        session.setCrop(10, 20, 100, 80)

        session.exportVideo(str(tmp_path / "out.mp4"))

        edit_spec = calls[0][1]
        assert edit_spec.crop is not None
        assert edit_spec.crop.x == 10


def marker_times(markers: list) -> list[float]:
    """Extract times from marker objects."""
    return [m["time"] for m in markers]
