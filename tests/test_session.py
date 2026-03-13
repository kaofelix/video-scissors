"""Tests for the editor session model."""

from pathlib import Path

from video_scissors.session import EditorSession


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

    def test_source_video_is_immutable_after_load(self, test_video: Path):
        """Source video doesn't change when working video changes."""
        session = EditorSession()
        session.load(test_video)

        new_working = Path("/tmp/edited.mp4")
        session.set_working_video(new_working)

        assert session.source_video == test_video
        assert session.working_video == new_working

    def test_has_video_returns_false_when_empty(self):
        """has_video is False for empty session."""
        session = EditorSession()

        assert session.has_video is False

    def test_has_video_returns_true_after_load(self, test_video: Path):
        """has_video is True after loading."""
        session = EditorSession()
        session.load(test_video)

        assert session.has_video is True

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
        """Can undo after an edit changes the working video."""
        session = EditorSession()
        session.load(test_video)

        session.set_working_video(Path("/tmp/edited.mp4"))

        assert session.can_undo is True

    def test_undo_restores_previous_working_video(self, test_video: Path):
        """Undo restores the previous working video."""
        session = EditorSession()
        session.load(test_video)
        edited = Path("/tmp/edited.mp4")
        session.set_working_video(edited)

        session.undo()

        assert session.working_video == test_video

    def test_can_redo_after_undo(self, test_video: Path):
        """Can redo after undoing an edit."""
        session = EditorSession()
        session.load(test_video)
        edited = Path("/tmp/edited.mp4")
        session.set_working_video(edited)
        session.undo()

        assert session.can_redo is True

    def test_redo_restores_undone_working_video(self, test_video: Path):
        """Redo restores the working video that was undone."""
        session = EditorSession()
        session.load(test_video)
        edited = Path("/tmp/edited.mp4")
        session.set_working_video(edited)
        session.undo()

        session.redo()

        assert session.working_video == edited

    def test_cannot_undo_after_undo_exhausted(self, test_video: Path):
        """Cannot undo when history is exhausted."""
        session = EditorSession()
        session.load(test_video)
        session.set_working_video(Path("/tmp/edited.mp4"))
        session.undo()

        assert session.can_undo is False

    def test_cannot_redo_after_redo_exhausted(self, test_video: Path):
        """Cannot redo when redo stack is exhausted."""
        session = EditorSession()
        session.load(test_video)
        session.set_working_video(Path("/tmp/edited.mp4"))
        session.undo()
        session.redo()

        assert session.can_redo is False

    def test_new_edit_clears_redo_stack(self, test_video: Path):
        """Making a new edit after undo clears the redo stack."""
        session = EditorSession()
        session.load(test_video)
        session.set_working_video(Path("/tmp/edit1.mp4"))
        session.undo()
        session.set_working_video(Path("/tmp/edit2.mp4"))

        assert session.can_redo is False

    def test_multiple_undo_redo(self, test_video: Path):
        """Multiple edits can be undone and redone in sequence."""
        session = EditorSession()
        session.load(test_video)
        edit1 = Path("/tmp/edit1.mp4")
        edit2 = Path("/tmp/edit2.mp4")
        session.set_working_video(edit1)
        session.set_working_video(edit2)

        session.undo()
        assert session.working_video == edit1

        session.undo()
        assert session.working_video == test_video

        session.redo()
        assert session.working_video == edit1

        session.redo()
        assert session.working_video == edit2

    def test_close_clears_undo_redo_history(self, test_video: Path):
        """Closing the session clears undo/redo history."""
        session = EditorSession()
        session.load(test_video)
        session.set_working_video(Path("/tmp/edited.mp4"))
        session.undo()
        session.close()

        assert session.can_undo is False
        assert session.can_redo is False

    def test_loading_new_video_clears_previous_history(self, test_video: Path, tmp_path: Path):
        """Opening a new video starts a fresh history for the session."""
        session = EditorSession()
        session.load(test_video)
        session.set_working_video(tmp_path / "edit1.mp4")

        new_video = tmp_path / "new_source.mp4"
        session.load(new_video)

        assert session.source_video == new_video
        assert session.working_video == new_video
        assert session.can_undo is False
        assert session.can_redo is False

    def test_working_video_revision_changes_on_working_video_transitions(
        self, test_video: Path, tmp_path: Path
    ):
        """Working video revision changes whenever the current working video changes."""
        session = EditorSession()

        assert session.working_video_revision == 0

        session.load(test_video)
        after_load = session.working_video_revision

        session.set_working_video(tmp_path / "edit1.mp4")
        after_edit = session.working_video_revision

        session.undo()
        after_undo = session.working_video_revision

        session.redo()
        after_redo = session.working_video_revision

        session.close()
        after_close = session.working_video_revision

        assert after_load > 0
        assert after_edit > after_load
        assert after_undo > after_edit
        assert after_redo > after_undo
        assert after_close > after_redo


class TestCutMarkers:
    """Tests for cut marker management in EditorSession."""

    def test_session_starts_with_no_markers(self):
        """A new session has no cut markers."""
        session = EditorSession()

        assert session.markers == ()

    def test_add_marker(self, test_video: Path):
        """Can add a cut marker at a specific time."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(1.5)

        assert session.markers == (1.5,)

    def test_markers_are_sorted(self, test_video: Path):
        """Markers are always returned in sorted order."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(3.0)
        session.add_marker(1.0)
        session.add_marker(2.0)

        assert session.markers == (1.0, 2.0, 3.0)

    def test_duplicate_markers_ignored(self, test_video: Path):
        """Adding a marker at the same time is ignored."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(1.5)
        session.add_marker(1.5)

        assert session.markers == (1.5,)

    def test_remove_marker(self, test_video: Path):
        """Can remove a marker by its time."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.remove_marker(1.0)

        assert session.markers == (2.0,)

    def test_remove_nonexistent_marker_is_noop(self, test_video: Path):
        """Removing a marker that doesn't exist does nothing."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        session.remove_marker(5.0)  # doesn't exist

        assert session.markers == (1.0,)

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

    def test_move_marker(self, test_video: Path):
        """Can move a marker to a new position."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.move_marker(1.0, 1.5)

        assert session.markers == (1.5, 2.0)

    def test_move_marker_maintains_sort(self, test_video: Path):
        """Moving a marker keeps markers sorted."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)
        session.add_marker(3.0)

        session.move_marker(1.0, 2.5)

        assert session.markers == (2.0, 2.5, 3.0)

    def test_move_nonexistent_marker_is_noop(self, test_video: Path):
        """Moving a marker that doesn't exist does nothing."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        session.move_marker(5.0, 2.0)

        assert session.markers == (1.0,)


class TestMarkerUndoRedo:
    """Tests for undo/redo of marker operations."""

    def test_add_marker_is_undoable(self, test_video: Path):
        """Adding a marker can be undone."""
        session = EditorSession()
        session.load(test_video)

        session.add_marker(1.5)
        assert session.markers == (1.5,)

        session.undo()
        assert session.markers == ()

    def test_add_marker_is_redoable(self, test_video: Path):
        """Undone marker add can be redone."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.5)
        session.undo()

        session.redo()

        assert session.markers == (1.5,)

    def test_remove_marker_is_undoable(self, test_video: Path):
        """Removing a marker can be undone."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.remove_marker(1.0)
        assert session.markers == (2.0,)

        session.undo()
        assert session.markers == (1.0, 2.0)

    def test_clear_markers_is_undoable(self, test_video: Path):
        """Clearing markers can be undone."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.clear_markers()
        assert session.markers == ()

        session.undo()
        assert session.markers == (1.0, 2.0)

    def test_move_marker_is_undoable(self, test_video: Path):
        """Moving a marker can be undone."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)
        session.add_marker(2.0)

        session.move_marker(1.0, 1.5)
        assert session.markers == (1.5, 2.0)

        session.undo()
        assert session.markers == (1.0, 2.0)

    def test_marker_state_preserved_across_video_edit_undo(self, test_video: Path, tmp_path: Path):
        """Marker state is preserved when undoing video edits."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.0)

        # Simulate a video edit (e.g., crop)
        edited = tmp_path / "edited.mp4"
        edited.touch()
        session.set_working_video(edited)

        # Add another marker after edit
        session.add_marker(2.0)

        # Undo the second marker add
        session.undo()
        assert session.markers == (1.0,)
        assert session.working_video == edited

        # Undo the video edit
        session.undo()
        assert session.markers == (1.0,)
        assert session.working_video == test_video


class TestMarkerAdjustmentOnCut:
    """Tests for marker time adjustment when cuts are applied."""

    def test_markers_before_cut_unchanged(self, test_video: Path, tmp_path: Path):
        """Markers before the cut region stay at their original time."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(0.5)  # Before cut region

        # Simulate cut from 1.0 to 2.0 (1 second removed)
        edited = tmp_path / "cut.mp4"
        edited.touch()
        session.apply_cut(1.0, 2.0, edited)

        assert 0.5 in session.markers

    def test_markers_inside_cut_removed(self, test_video: Path, tmp_path: Path):
        """Markers inside the cut region are removed."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(1.5)  # Inside cut region [1.0, 2.0]

        edited = tmp_path / "cut.mp4"
        edited.touch()
        session.apply_cut(1.0, 2.0, edited)

        assert 1.5 not in session.markers

    def test_markers_after_cut_shifted(self, test_video: Path, tmp_path: Path):
        """Markers after the cut region are shifted earlier by cut duration."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(3.0)  # After cut region [1.0, 2.0]

        edited = tmp_path / "cut.mp4"
        edited.touch()
        session.apply_cut(1.0, 2.0, edited)  # 1 second removed

        # Marker should shift from 3.0 to 2.0 (shifted by 1 second)
        assert 2.0 in session.markers
        assert 3.0 not in session.markers

    def test_complex_marker_adjustment(self, test_video: Path, tmp_path: Path):
        """Multiple markers are correctly adjusted on cut."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(0.5)  # Before - unchanged
        session.add_marker(1.5)  # Inside - removed
        session.add_marker(2.5)  # After - shifted to 1.5
        session.add_marker(4.0)  # After - shifted to 3.0

        edited = tmp_path / "cut.mp4"
        edited.touch()
        session.apply_cut(1.0, 2.0, edited)  # 1 second removed

        assert session.markers == (0.5, 1.5, 3.0)

    def test_cut_with_markers_is_undoable(self, test_video: Path, tmp_path: Path):
        """Undoing a cut restores original marker positions."""
        session = EditorSession()
        session.load(test_video)
        session.add_marker(0.5)
        session.add_marker(1.5)
        session.add_marker(3.0)

        edited = tmp_path / "cut.mp4"
        edited.touch()
        session.apply_cut(1.0, 2.0, edited)

        session.undo()

        assert session.markers == (0.5, 1.5, 3.0)
