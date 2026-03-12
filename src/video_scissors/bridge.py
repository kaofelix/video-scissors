"""QML/Python bridge for the editor session.

This module provides the narrow interface between QML and Python.
QML interacts with the session through this bridge only.
"""

import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from video_scissors.edit_service import FFmpegEditService
from video_scissors.services import CropRequest
from video_scissors.session import EditorSession
from video_scissors.thumbnails import ThumbnailExtractor


class SessionBridge(QObject):
    """Bridge exposing EditorSession to QML.

    Provides properties and slots for QML to interact with the session.
    Emits signals when state changes so QML can react.
    """

    videoChanged = Signal()
    thumbnailsReady = Signal(list)  # List of file:// URLs

    def __init__(
        self,
        session: EditorSession,
        parent: QObject | None = None,
        edit_output_dir: Path | None = None,
    ):
        super().__init__(parent)
        self._session = session
        # Use session-specific temp dir (cleaned up by OS)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="video_scissors_"))
        self._thumbnail_dir = self._temp_dir / "thumbnails"
        self._thumbnail_dir.mkdir(exist_ok=True)
        self._thumbnail_extractor = ThumbnailExtractor(cache_dir=self._thumbnail_dir)
        # Edit output directory (for crop/cut results)
        self._edit_output_dir = edit_output_dir or (self._temp_dir / "edits")
        self._edit_output_dir.mkdir(exist_ok=True)
        self._edit_service = FFmpegEditService(output_dir=self._edit_output_dir)

    @Property(bool, notify=videoChanged)
    def hasVideo(self) -> bool:
        """True if a video is loaded."""
        return self._session.has_video

    @Property(str, notify=videoChanged)
    def workingVideoUrl(self) -> str:
        """The working video as a file:// URL for QML."""
        if self._session.working_video is None:
            return ""
        return self._session.working_video.as_uri()

    @Property(int, notify=videoChanged)
    def videoWidth(self) -> int:
        """Width of the loaded video in pixels."""
        return self._session.video_width

    @Property(int, notify=videoChanged)
    def videoHeight(self) -> int:
        """Height of the loaded video in pixels."""
        return self._session.video_height

    @Property(bool, notify=videoChanged)
    def canUndo(self) -> bool:
        """True if there are edits that can be undone."""
        return self._session.can_undo

    @Property(bool, notify=videoChanged)
    def canRedo(self) -> bool:
        """True if there are undone edits that can be redone."""
        return self._session.can_redo

    @Slot(str)
    def openFile(self, path: str) -> None:
        """Open a video file."""
        self._session.load(Path(path))
        self.videoChanged.emit()

    @Slot()
    def close(self) -> None:
        """Close the current session."""
        self._session.close()
        self.videoChanged.emit()

    @Slot(str)
    def setWorkingVideo(self, path: str) -> None:
        """Update the working video path (after an edit)."""
        self._session.set_working_video(Path(path))
        self.videoChanged.emit()

    @Slot()
    def undo(self) -> None:
        """Undo the last edit."""
        if self._session.can_undo:
            self._session.undo()
            self.videoChanged.emit()

    @Slot()
    def redo(self) -> None:
        """Redo the last undone edit."""
        if self._session.can_redo:
            self._session.redo()
            self.videoChanged.emit()

    @Slot(int, int, int, int)
    def applyCrop(self, x: int, y: int, width: int, height: int) -> None:
        """Apply a crop operation to the working video."""
        if self._session.working_video is None:
            return
        request = CropRequest(x=x, y=y, width=width, height=height)
        result = self._edit_service.apply_crop(self._session.working_video, request)
        self._session.set_working_video(result.output_path)
        self.videoChanged.emit()

    @Slot(int, int)
    def requestThumbnails(self, frame_count: int, thumb_height: int) -> None:
        """Request thumbnail extraction in background thread.

        Args:
            frame_count: Number of frames to extract
            thumb_height: Height of each thumbnail in pixels
        """
        video_path = self._session.working_video
        if video_path is None or frame_count <= 0:
            self.thumbnailsReady.emit([])
            return

        def extract_and_emit():
            frames = self._thumbnail_extractor.extract(video_path, frame_count, thumb_height)
            urls = [f"file://{path}" for path in frames]
            # Emit signal (safe from thread via Qt's queued connections)
            self.thumbnailsReady.emit(urls)

        thread = threading.Thread(target=extract_and_emit, daemon=True)
        thread.start()
