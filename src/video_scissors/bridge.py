"""QML/Python bridge for the editor session.

This module provides the narrow interface between QML and Python.
QML interacts with the session through this bridge only.
"""

import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from video_scissors.session import EditorSession
from video_scissors.thumbnails import ThumbnailExtractor


class SessionBridge(QObject):
    """Bridge exposing EditorSession to QML.

    Provides properties and slots for QML to interact with the session.
    Emits signals when state changes so QML can react.
    """

    videoChanged = Signal()
    thumbnailsReady = Signal(list)  # List of file:// URLs

    def __init__(self, session: EditorSession, parent: QObject | None = None):
        super().__init__(parent)
        self._session = session
        self._thumbnail_extractor = ThumbnailExtractor(
            cache_dir=Path(tempfile.gettempdir()) / "video_scissors_thumbnails"
        )

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
