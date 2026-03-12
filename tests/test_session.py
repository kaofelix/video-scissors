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
