"""Tests for the QML/Python bridge."""

import tempfile
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


class TestBridgeUndoRedo:
    """Tests for undo/redo operations via bridge."""

    def test_can_undo_exposed(self, test_video: Path):
        """Bridge exposes canUndo property."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        assert bridge.canUndo is False

    def test_can_redo_exposed(self, test_video: Path):
        """Bridge exposes canRedo property."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        assert bridge.canRedo is False

    def test_undo_restores_previous_video(self, test_video: Path, tmp_path: Path):
        """Undo restores the previous working video."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        bridge.undo()

        assert str(test_video) in bridge.workingVideoUrl

    def test_redo_restores_undone_video(self, test_video: Path, tmp_path: Path):
        """Redo restores the undone working video."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))
        bridge.undo()

        bridge.redo()

        assert str(edited) in bridge.workingVideoUrl

    def test_undo_emits_video_changed(self, test_video: Path, tmp_path: Path):
        """Undo emits videoChanged signal."""
        session = EditorSession()
        session.load(test_video)
        bridge = SessionBridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        signals = []
        bridge.videoChanged.connect(lambda: signals.append(True))
        bridge.undo()

        assert len(signals) == 1


class TestBridgeCrop:
    """Tests for crop operation via bridge."""

    def test_apply_crop_changes_working_video(self, test_video: Path):
        """applyCrop produces new working video with cropped dimensions."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = SessionBridge(session, edit_output_dir=Path(tmp))

            # test_video is 320x240, crop to 160x120
            bridge.applyCrop(0, 0, 160, 120)

            # Working video should have changed
            assert session.working_video != test_video
            assert session.working_video.exists()

    def test_apply_crop_emits_video_changed(self, test_video: Path):
        """applyCrop emits videoChanged signal."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = SessionBridge(session, edit_output_dir=Path(tmp))

            signals = []
            bridge.videoChanged.connect(lambda: signals.append(True))
            bridge.applyCrop(0, 0, 160, 120)

            assert len(signals) == 1

    def test_crop_can_be_undone(self, test_video: Path):
        """Crop operation can be undone."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = SessionBridge(session, edit_output_dir=Path(tmp))
            bridge.applyCrop(0, 0, 160, 120)

            assert bridge.canUndo is True
            bridge.undo()
            assert str(test_video) in bridge.workingVideoUrl
