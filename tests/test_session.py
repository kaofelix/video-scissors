"""Tests for the editor session model."""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QUndoStack

from video_scissors.document import EditSpec
from video_scissors.session import EditorSession, Marker


class TestQUndoStackIntegration:
    """Tests for QUndoStack-based undo/redo."""

    def test_session_is_qobject(self):
        """EditorSession is a QObject (required for QUndoStack ownership)."""
        session = EditorSession()
        assert isinstance(session, QObject)

    def test_session_has_undo_stack(self, test_video: Path):
        """EditorSession exposes QUndoStack via undo_stack property."""
        session = EditorSession()
        session.load(test_video)

        assert hasattr(session, "undo_stack")
        assert isinstance(session.undo_stack, QUndoStack)

    def test_undo_stack_can_undo_changed_signal(self, test_video: Path, qtbot):
        """QUndoStack emits canUndoChanged when undo state changes."""
        session = EditorSession()
        session.load(test_video)

        with qtbot.waitSignal(session.undo_stack.canUndoChanged, timeout=1000):
            session.add_marker(1.0)

    def test_undo_stack_can_redo_changed_signal(self, test_video: Path, qtbot):
        """QUndoStack emits canRedoChanged when redo state changes."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        with qtbot.waitSignal(session.undo_stack.canRedoChanged, timeout=1000):
            session.undo()

    def test_undo_text_available(self, test_video: Path):
        """undoText describes the operation to undo."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.5)

        # Should have some descriptive text
        assert session.undo_stack.undoText() != ""

    def test_redo_text_available(self, test_video: Path):
        """redoText describes the operation to redo."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.5)
        session.undo()

        # Should have some descriptive text
        assert session.undo_stack.redoText() != ""


class TestMarker:
    """Tests for the Marker dataclass."""

    def test_marker_has_id_and_time(self):
        """Marker stores id and time."""
        marker = Marker(id="abc123", time=1.5)

        assert marker.id == "abc123"
        assert marker.time == 1.5

    def test_marker_create_generates_unique_ids(self):
        """Marker.create generates unique IDs."""
        marker1 = Marker.create(1.0)
        marker2 = Marker.create(2.0)

        assert marker1.id != marker2.id
        assert len(marker1.id) == 32  # UUID hex length

    def test_marker_is_immutable(self):
        """Marker is frozen (immutable)."""
        marker = Marker(id="abc", time=1.0)

        with pytest.raises(AttributeError):
            marker.time = 2.0  # type: ignore


class TestEditorSession:
    """Tests for EditorSession - the core editing state container."""

    def test_session_starts_empty(self):
        """A new session has no video loaded."""
        session = EditorSession()

        assert session.source_video is None
        assert session.working_video is None

    def test_load_video_sets_source_and_working(self, test_video: Path):
        """Loading a video sets both source and working video."""
        session = EditorSession()
        session.load(test_video)

        assert session.source_video == test_video
        assert session.working_video == test_video

    def test_has_video_returns_false_when_empty(self):
        """has_video is False for empty session."""
        session = EditorSession()

        assert session.has_video is False

    def test_has_video_returns_true_after_load(self, test_video: Path):
        """has_video is True after loading."""
        session = EditorSession()
        session.load(test_video)

        assert session.has_video is True

    def test_video_frame_rate_available_after_load(self, test_video: Path):
        """Frame rate is available after loading a video."""
        session = EditorSession()
        session.load(test_video)

        # Test video is generated at 30fps
        assert session.video_frame_rate == 30.0

    def test_video_frame_rate_zero_when_no_video(self):
        """Frame rate is 0 when no video is loaded."""
        session = EditorSession()

        assert session.video_frame_rate == 0.0

    def test_close_clears_session(self, test_video: Path):
        """Closing returns session to empty state."""
        session = EditorSession()
        session.load(test_video)
        session.close()

        assert session.source_video is None
        assert session.working_video is None
        assert session.has_video is False


class TestUndoRedo:
    """Tests for undo/redo functionality in EditorSession."""

    def test_can_undo_is_false_initially(self, test_video: Path):
        """Cannot undo when no edits have been made."""
        session = EditorSession()
        session.load(test_video)

        assert session.can_undo is False

    def test_can_redo_is_false_initially(self, test_video: Path):
        """Cannot redo when nothing has been undone."""
        session = EditorSession()
        session.load(test_video)

        assert session.can_redo is False

    def test_can_undo_after_edit(self, test_video: Path):
        """Can undo after an edit."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(1.0)

        assert session.can_undo is True

    def test_can_redo_after_undo(self, test_video: Path):
        """Can redo after undoing an edit."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.undo()

        assert session.can_redo is True

    def test_cannot_undo_after_undo_exhausted(self, test_video: Path):
        """Cannot undo when history is exhausted."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.undo()

        assert session.can_undo is False

    def test_cannot_redo_after_redo_exhausted(self, test_video: Path):
        """Cannot redo when redo stack is exhausted."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.undo()
        session.redo()

        assert session.can_redo is False

    def test_new_edit_clears_redo_stack(self, test_video: Path):
        """Making a new edit after undo clears the redo stack."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.undo()
        session.add_marker(2.0)

        assert session.can_redo is False

    def test_close_clears_undo_redo_history(self, test_video: Path):
        """Closing the session clears undo/redo history."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.undo()
        session.close()

        assert session.can_undo is False
        assert session.can_redo is False

    def test_loading_new_video_clears_previous_history(self, test_video: Path, tmp_path: Path):
        """Opening a new video starts a fresh history for the session."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        new_video = tmp_path / "new_source.mp4"
        session.load(new_video)

        assert session.source_video == new_video
        assert session.working_video == new_video
        assert session.can_undo is False
        assert session.can_redo is False

    def test_working_video_revision_changes_on_load_and_close(
        self, test_video: Path, tmp_path: Path
    ):
        """Working video revision changes on load and close."""
        session = EditorSession()

        assert session.working_video_revision == 0

        session.load(test_video)
        after_load = session.working_video_revision

        session.close()
        after_close = session.working_video_revision

        assert after_load > 0
        assert after_close > after_load


def marker_times(markers: tuple[Marker, ...]) -> tuple[float, ...]:
    """Helper to extract times from markers for assertions."""
    return tuple(m.time for m in markers)


class TestCutMarkers:
    """Tests for cut marker management in EditorSession."""

    def test_session_starts_with_no_markers(self):
        """A new session has no cut markers."""
        session = EditorSession()

        assert session.markers == ()

    def test_add_marker_returns_marker_with_id(self, test_video: Path):
        """Adding a marker returns the created Marker with an ID."""
        session = EditorSession()
        session.load(test_video)

        marker = session.add_marker(1.5)

        assert marker is not None
        assert marker.time == 1.5
        assert len(marker.id) == 32

    def test_add_marker_stores_marker(self, test_video: Path):
        """Added marker appears in markers list."""
        session = EditorSession()
        session.load(test_video)

        marker = session.add_marker(1.5)

        assert len(session.markers) == 1
        assert session.markers[0].id == marker.id
        assert session.markers[0].time == 1.5

    def test_markers_are_sorted_by_time(self, test_video: Path):
        """Markers are always returned sorted by time."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(3.0)
        session.add_marker(1.0)
        session.add_marker(2.0)

        assert marker_times(session.markers) == (1.0, 2.0, 3.0)

    def test_duplicate_time_markers_ignored(self, test_video: Path):
        """Adding a marker at the same time is ignored."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(1.5)
        result = session.add_marker(1.5)

        assert result is None
        assert len(session.markers) == 1

    def test_remove_marker_by_id(self, test_video: Path):
        """Can remove a marker by its ID."""
        session = EditorSession()
        session.load(test_video)
        marker1 = session.add_marker(1.0)
        session.add_marker(2.0)

        session.remove_marker(marker1.id)

        assert marker_times(session.markers) == (2.0,)

    def test_remove_nonexistent_marker_is_noop(self, test_video: Path):
        """Removing a marker ID that doesn't exist does nothing."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        session.remove_marker("nonexistent-id")

        assert len(session.markers) == 1

    def test_clear_markers(self, test_video: Path):
        """Can clear all markers at once."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.clear_markers()

        assert session.markers == ()

    def test_loading_video_clears_markers(self, test_video: Path, tmp_path: Path):
        """Loading a new video clears existing markers."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        new_video = tmp_path / "new.mp4"
        new_video.touch()
        session.load(new_video)

        assert session.markers == ()

    def test_close_clears_markers(self, test_video: Path):
        """Closing the session clears markers."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        session.close()

        assert session.markers == ()

    def test_move_marker_by_id(self, test_video: Path):
        """Can move a marker to a new position by ID."""
        session = EditorSession()
        session.load(test_video)
        marker1 = session.add_marker(1.0)
        session.add_marker(2.0)

        session.move_marker(marker1.id, 1.5)

        assert marker_times(session.markers) == (1.5, 2.0)

    def test_move_marker_maintains_sort(self, test_video: Path):
        """Moving a marker keeps markers sorted."""
        session = EditorSession()
        session.load(test_video)
        marker1 = session.add_marker(1.0)
        session.add_marker(2.0)
        session.add_marker(3.0)

        session.move_marker(marker1.id, 2.5)

        assert marker_times(session.markers) == (2.0, 2.5, 3.0)

    def test_move_marker_preserves_id(self, test_video: Path):
        """Moving a marker preserves its ID."""
        session = EditorSession()
        session.load(test_video)
        marker = session.add_marker(1.0)
        original_id = marker.id

        session.move_marker(marker.id, 2.0)

        assert session.markers[0].id == original_id
        assert session.markers[0].time == 2.0

    def test_move_nonexistent_marker_is_noop(self, test_video: Path):
        """Moving a marker ID that doesn't exist does nothing."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        session.move_marker("nonexistent-id", 2.0)

        assert len(session.markers) == 1


class TestMarkerUndoRedo:
    """Tests for undo/redo of marker operations."""

    def test_add_marker_is_undoable(self, test_video: Path):
        """Adding a marker can be undone."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(1.5)
        assert marker_times(session.markers) == (1.5,)

        session.undo()
        assert session.markers == ()

    def test_add_marker_is_redoable(self, test_video: Path):
        """Undone marker add can be redone."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.5)
        session.undo()

        session.redo()

        assert marker_times(session.markers) == (1.5,)

    def test_remove_marker_is_undoable(self, test_video: Path):
        """Removing a marker can be undone."""
        session = EditorSession()
        session.load(test_video)
        marker1 = session.add_marker(1.0)
        session.add_marker(2.0)

        session.remove_marker(marker1.id)
        assert marker_times(session.markers) == (2.0,)

        session.undo()
        assert marker_times(session.markers) == (1.0, 2.0)

    def test_clear_markers_is_undoable(self, test_video: Path):
        """Clearing markers can be undone."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.clear_markers()
        assert session.markers == ()

        session.undo()
        assert marker_times(session.markers) == (1.0, 2.0)

    def test_move_marker_is_undoable(self, test_video: Path):
        """Moving a marker can be undone."""
        session = EditorSession()
        session.load(test_video)
        marker1 = session.add_marker(1.0)
        session.add_marker(2.0)

        session.move_marker(marker1.id, 1.5)
        assert marker_times(session.markers) == (1.5, 2.0)

        session.undo()
        assert marker_times(session.markers) == (1.0, 2.0)


class TestEditSpecIntegration:
    """Tests for non-destructive EditSpec-based editing."""

    def test_session_starts_with_empty_edit_spec(self, test_video: Path):
        """A loaded session has an empty EditSpec."""
        session = EditorSession()
        session.load(test_video)

        assert session._raw_document.edit_spec == EditSpec()

    def test_add_cut_updates_edit_spec(self, test_video: Path):
        """add_cut stores cut in EditSpec (non-destructive)."""
        session = EditorSession()
        session.load(test_video)

        session.add_cut(1.0, 2.0)

        assert len(session._raw_document.edit_spec.cuts) == 1
        assert session._raw_document.edit_spec.cuts[0].start == 1.0
        assert session._raw_document.edit_spec.cuts[0].end == 2.0

    def test_add_cut_is_instant(self, test_video: Path):
        """add_cut doesn't trigger any encoding (just updates EditSpec)."""
        session = EditorSession()
        session.load(test_video)
        original_video = session.source_video

        session.add_cut(1.0, 2.0)

        # Source video unchanged - no new file created
        assert session.source_video == original_video

    def test_add_cut_is_undoable(self, test_video: Path):
        """add_cut can be undone."""
        session = EditorSession()
        session.load(test_video)
        session.add_cut(1.0, 2.0)

        session.undo()

        assert session._raw_document.edit_spec.cuts == ()

    def test_add_cut_is_redoable(self, test_video: Path):
        """Undone cut can be redone."""
        session = EditorSession()
        session.load(test_video)
        session.add_cut(1.0, 2.0)
        session.undo()

        session.redo()

        assert len(session._raw_document.edit_spec.cuts) == 1

    def test_set_crop_updates_edit_spec(self, test_video: Path):
        """set_crop stores crop in EditSpec (non-destructive)."""
        session = EditorSession()
        session.load(test_video)

        session.set_crop(10, 20, 100, 80)

        assert session._raw_document.edit_spec.crop is not None
        assert session._raw_document.edit_spec.crop.x == 10
        assert session._raw_document.edit_spec.crop.width == 100

    def test_set_crop_is_undoable(self, test_video: Path):
        """set_crop can be undone."""
        session = EditorSession()
        session.load(test_video)
        session.set_crop(10, 20, 100, 80)

        session.undo()

        assert session._raw_document.edit_spec.crop is None

    def test_multiple_cuts_accumulate(self, test_video: Path):
        """Multiple cuts accumulate in EditSpec."""
        session = EditorSession()
        session.load(test_video)

        session.add_cut(1.0, 2.0)
        session.add_cut(4.0, 5.0)

        assert len(session._raw_document.edit_spec.cuts) == 2

    def test_edit_spec_reset_on_new_video(self, test_video: Path, tmp_path: Path):
        """Loading a new video resets EditSpec."""
        session = EditorSession()
        session.load(test_video)
        session.add_cut(1.0, 2.0)

        new_video = tmp_path / "new.mp4"
        new_video.touch()
        session.load(new_video)

        assert session._raw_document.edit_spec == EditSpec()

    def test_source_duration_available(self, test_video: Path):
        """Source duration is available for EditSpec calculations."""
        session = EditorSession()
        session.load(test_video)

        # Test video is 2 seconds
        assert session.source_duration == 2.0

    def test_effective_duration_reflects_cuts(self, test_video: Path):
        """effective_duration accounts for cuts."""
        session = EditorSession()
        session.load(test_video)
        # Test video is 2 seconds
        session.add_cut(0.5, 1.0)  # Remove 0.5 seconds

        assert session.effective_duration == 1.5
