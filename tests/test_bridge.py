"""Tests for the QML/Python bridge."""

from pathlib import Path

from conftest import generate_test_video
from video_scissors.bridge import SessionBridge
from video_scissors.session import EditorSession


class TestSessionBridge:
    """Tests for SessionBridge - the QML-facing API."""

    def test_bridge_exposes_has_video(self):
        """Bridge exposes hasVideo property."""
        session = EditorSession()
        bridge = SessionBridge(session)

        assert bridge.hasVideo is False

    def test_bridge_exposes_working_video_path(self, test_video: Path):
        """Bridge exposes workingVideoUrl for QML."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        # QML needs file:// URLs
        assert bridge.workingVideoUrl.startswith("file://")
        assert str(test_video) in bridge.workingVideoUrl

    def test_bridge_returns_empty_url_when_no_video(self):
        """Bridge returns empty string when no video loaded."""
        session = EditorSession()
        bridge = SessionBridge(session)

        assert bridge.workingVideoUrl == ""

    def test_open_file_loads_into_session(self, test_video: Path):
        """openFile loads the video into the session."""
        session = EditorSession()
        bridge = SessionBridge(session)

        bridge.openFile(str(test_video))

        assert session.has_video is True
        assert session.source_video == test_video

    def test_open_file_emits_video_changed_signal(self, test_video: Path):
        """openFile emits videoChanged signal."""
        session = EditorSession()
        bridge = SessionBridge(session)

        signal_received = []
        bridge.videoChanged.connect(lambda: signal_received.append(True))

        bridge.openFile(str(test_video))

        assert len(signal_received) == 1

    def test_close_clears_session(self, test_video: Path):
        """close clears the session."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        bridge.close()

        assert session.has_video is False

    def test_reload_updates_working_video(self, test_video: Path, tmp_path: Path):
        """Reloading with new path updates workingVideoUrl."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        # Simulate an edit producing a new working video
        new_video = tmp_path / "edited.mp4"
        generate_test_video(new_video, duration=1.0)

        bridge.setWorkingVideo(str(new_video))

        assert str(new_video) in bridge.workingVideoUrl
        # Source unchanged
        assert session.source_video == test_video
