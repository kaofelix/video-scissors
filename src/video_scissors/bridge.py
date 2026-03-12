"""QML/Python bridge for the editor session.

This module provides the narrow interface between QML and Python.
QML interacts with the session through this bridge only.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from video_scissors.session import EditorSession


class SessionBridge(QObject):
    """Bridge exposing EditorSession to QML.

    Provides properties and slots for QML to interact with the session.
    Emits signals when state changes so QML can react.
    """

    videoChanged = Signal()

    def __init__(self, session: EditorSession, parent: QObject | None = None):
        super().__init__(parent)
        self._session = session

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
