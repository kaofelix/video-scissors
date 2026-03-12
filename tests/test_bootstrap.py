"""Tests for application/service composition."""

from pathlib import Path

from video_scissors.bootstrap import create_session_bridge
from video_scissors.session import EditorSession


class TestCreateSessionBridge:
    """Default service wiring should live outside SessionBridge itself."""

    def test_create_session_bridge_creates_workspace_directories(self, tmp_path: Path):
        """Composition creates the expected workspace directories for the session."""
        session = EditorSession()

        create_session_bridge(session, workspace_dir=tmp_path)

        assert (tmp_path / "thumbnails").is_dir()
        assert (tmp_path / "edits").is_dir()

    def test_create_session_bridge_places_crop_outputs_in_edit_workspace(
        self, test_video: Path, tmp_path: Path
    ):
        """The composed bridge writes edit outputs under the edit workspace."""
        session = EditorSession()
        bridge = create_session_bridge(session, workspace_dir=tmp_path)
        bridge.openFile(str(test_video))

        bridge.applyCrop(0, 0, 160, 120)

        assert session.working_video is not None
        assert session.working_video.parent == tmp_path / "edits"
