"""Tests for application/service composition."""

from pathlib import Path

from video_scissors.bootstrap import create_session


class TestCreateSession:
    """Default service wiring should live outside EditorSession itself."""

    def test_create_session_creates_workspace_directories(self, tmp_path: Path):
        """Composition creates the expected workspace directories for the session."""
        create_session(workspace_dir=tmp_path)

        assert (tmp_path / "thumbnails").is_dir()

    def test_create_session_returns_functional_session(self, test_video: Path, tmp_path: Path):
        """The composed session can load a video and perform edits."""
        session = create_session(workspace_dir=tmp_path)
        session.openFile(str(test_video))

        assert session.hasVideo is True
        assert session.source_video == test_video
