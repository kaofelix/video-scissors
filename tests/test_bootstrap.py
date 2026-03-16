"""Tests for application/service composition."""

from pathlib import Path

from video_scissors.bootstrap import create_session


class TestCreateSession:
    """Default service wiring should live outside EditorSession itself."""

    def test_create_session_creates_workspace_directories(self, tmp_path: Path):
        """Composition creates the expected workspace directories for the session."""
        create_session(workspace_dir=tmp_path)

        assert (tmp_path / "thumbnails").is_dir()
        assert (tmp_path / "edits").is_dir()

    def test_create_session_places_crop_outputs_in_edit_workspace(
        self, test_video: Path, tmp_path: Path
    ):
        """The composed session writes edit outputs under the edit workspace."""
        session = create_session(workspace_dir=tmp_path)
        session.openFile(str(test_video))

        session.applyCrop(0, 0, 160, 120)

        assert session.working_video is not None
        assert session.working_video.parent == tmp_path / "edits"
