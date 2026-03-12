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
