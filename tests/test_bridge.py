"""Tests for the QML/Python bridge."""

import tempfile
from pathlib import Path

from conftest import generate_test_video
from video_scissors.bootstrap import create_session_bridge
from video_scissors.bridge import SessionBridge
from video_scissors.services import EditResult
from video_scissors.session import EditorSession


class FakeThumbnailExtractor:
    """Test double for thumbnail extraction."""

    def __init__(self, frames: list[Path]):
        self.frames = frames
        self.calls: list[tuple[Path, int, int]] = []

    def extract(self, video_path: Path, frame_count: int, thumb_height: int) -> list[Path]:
        self.calls.append((video_path, frame_count, thumb_height))
        return self.frames


class FakeEditService:
    """Test double for edit application."""

    def __init__(self, output_path: Path | None = None):
        self.output_path = output_path or Path("/tmp/fake-edit.mp4")

    def apply_crop(self, source: Path, request) -> EditResult:
        return EditResult(output_path=self.output_path)

    def apply_cut(self, source: Path, request) -> EditResult:
        return EditResult(output_path=self.output_path)


def make_bridge(
    session: EditorSession,
    thumbnail_extractor: FakeThumbnailExtractor | None = None,
    edit_service: FakeEditService | None = None,
) -> SessionBridge:
    """Create a SessionBridge with simple test doubles by default."""
    return SessionBridge(
        session,
        thumbnail_extractor=thumbnail_extractor or FakeThumbnailExtractor([]),
        edit_service=edit_service or FakeEditService(),
    )


class TestSessionBridge:
    """Tests for SessionBridge - the QML-facing API."""

    def test_bridge_exposes_has_video(self):
        """Bridge exposes hasVideo property."""
        session = EditorSession()
        bridge = make_bridge(session)

        assert bridge.hasVideo is False

    def test_bridge_exposes_working_video_path(self, test_video: Path):
        """Bridge exposes workingVideoUrl for QML."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.workingVideoUrl.startswith("file://")
        assert str(test_video) in bridge.workingVideoUrl

    def test_bridge_returns_empty_url_when_no_video(self):
        """Bridge returns empty string when no video loaded."""
        session = EditorSession()
        bridge = make_bridge(session)

        assert bridge.workingVideoUrl == ""

    def test_open_file_loads_into_session(self, test_video: Path):
        """openFile loads the video into the session."""
        session = EditorSession()
        bridge = make_bridge(session)

        bridge.openFile(str(test_video))

        assert session.has_video is True
        assert session.source_video == test_video

    def test_open_file_emits_video_changed_signal(self, test_video: Path):
        """openFile emits videoChanged signal."""
        session = EditorSession()
        bridge = make_bridge(session)

        signal_received = []
        bridge.videoChanged.connect(lambda: signal_received.append(True))

        bridge.openFile(str(test_video))

        assert len(signal_received) == 1

    def test_close_clears_session(self, test_video: Path):
        """close clears the session."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        bridge.close()

        assert session.has_video is False

    def test_reload_updates_working_video(self, test_video: Path, tmp_path: Path):
        """Reloading with new path updates workingVideoUrl."""
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        new_video = tmp_path / "edited.mp4"
        generate_test_video(new_video, duration=1.0)

        bridge.setWorkingVideo(str(new_video))

        assert str(new_video) in bridge.workingVideoUrl
        assert session.source_video == test_video


class TestBridgeUndoRedo:
    """Tests for undo/redo operations via bridge."""

    def test_can_undo_exposed(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.canUndo is False

    def test_can_redo_exposed(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        assert bridge.canRedo is False

    def test_undo_restores_previous_video(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))

        bridge.undo()

        assert str(test_video) in bridge.workingVideoUrl

    def test_redo_restores_undone_video(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))
        bridge.undo()

        bridge.redo()

        assert str(edited) in bridge.workingVideoUrl

    def test_undo_emits_video_changed(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        session.load(test_video)
        bridge = make_bridge(session)

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
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCrop(0, 0, 160, 120)

            assert session.working_video != test_video
            assert session.working_video is not None
            assert session.working_video.exists()

    def test_apply_crop_emits_video_changed(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            signals = []
            bridge.videoChanged.connect(lambda: signals.append(True))
            bridge.applyCrop(0, 0, 160, 120)

            assert len(signals) == 1

    def test_crop_can_be_undone(self, test_video: Path):
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCrop(0, 0, 160, 120)

            assert bridge.canUndo is True
            bridge.undo()
            assert str(test_video) in bridge.workingVideoUrl


class TestBridgeCut:
    """Tests for cut (segment removal) operation via bridge."""

    def test_apply_cut_changes_working_video(self, test_video: Path):
        """applyCut creates a new working video with the segment removed."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCut(0.5, 1.0)  # Remove 0.5 seconds

            assert session.working_video != test_video
            assert session.working_video is not None
            assert session.working_video.exists()

    def test_apply_cut_emits_video_changed(self, test_video: Path):
        """applyCut emits videoChanged signal."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))

            signals = []
            bridge.videoChanged.connect(lambda: signals.append(True))
            bridge.applyCut(0.5, 1.0)

            assert len(signals) == 1

    def test_cut_can_be_undone(self, test_video: Path):
        """Cut operation can be undone to restore original video."""
        session = EditorSession()
        session.load(test_video)

        with tempfile.TemporaryDirectory() as tmp:
            bridge = create_session_bridge(session, workspace_dir=Path(tmp))
            bridge.applyCut(0.5, 1.0)

            assert bridge.canUndo is True
            bridge.undo()
            assert str(test_video) in bridge.workingVideoUrl


class TestBridgeWorkingVideoRevision:
    """Tests for strategic working-video change tracking via the bridge."""

    def test_bridge_exposes_working_video_revision(self, test_video: Path, tmp_path: Path):
        session = EditorSession()
        bridge = make_bridge(session)

        assert bridge.workingVideoRevision == 0

        bridge.openFile(str(test_video))
        after_open = bridge.workingVideoRevision

        edited = tmp_path / "edited.mp4"
        generate_test_video(edited, duration=1.0)
        bridge.setWorkingVideo(str(edited))
        after_edit = bridge.workingVideoRevision

        bridge.undo()
        after_undo = bridge.workingVideoRevision

        assert after_open > 0
        assert after_edit > after_open
        assert after_undo > after_edit

    def test_request_thumbnails_ignores_stale_revision(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        session = EditorSession()
        session.load(test_video)
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        bridge = make_bridge(session, thumbnail_extractor=extractor)

        signals = []
        bridge.thumbnailsReady.connect(lambda urls: signals.append(urls))

        stale_revision = bridge.workingVideoRevision - 1
        bridge.requestThumbnails(3, 40, stale_revision)
        qtbot.wait(50)

        assert signals == []
        assert extractor.calls == []

    def test_request_thumbnails_emits_for_current_revision(
        self, test_video: Path, tmp_path: Path, qtbot
    ):
        session = EditorSession()
        session.load(test_video)
        fake_frame = tmp_path / "frame.jpg"
        fake_frame.write_text("not a real image")
        extractor = FakeThumbnailExtractor([fake_frame])
        bridge = make_bridge(session, thumbnail_extractor=extractor)

        signals = []
        bridge.thumbnailsReady.connect(lambda urls: signals.append(urls))

        bridge.requestThumbnails(3, 40, bridge.workingVideoRevision)
        qtbot.waitUntil(lambda: len(signals) == 1, timeout=1000)

        assert signals == [[f"file://{fake_frame}"]]
        assert extractor.calls == [(test_video, 3, 40)]
