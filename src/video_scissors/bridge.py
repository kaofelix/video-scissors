"""QML/Python bridge for the editor session.

This module provides the narrow interface between QML and Python.
QML interacts with the session through this bridge only.
"""

import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from video_scissors.services import CropRequest, CutRequest, EditService, ThumbnailExtractorProtocol
from video_scissors.session import EditorSession


class SessionBridge(QObject):
    """Bridge exposing EditorSession to QML.

    Provides properties and slots for QML to interact with the session.
    Emits signals when state changes so QML can react.
    """

    videoChanged = Signal()
    markersChanged = Signal()
    thumbnailsReady = Signal(list)  # List of file:// URLs

    def __init__(
        self,
        session: EditorSession,
        thumbnail_extractor: ThumbnailExtractorProtocol,
        edit_service: EditService,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._session = session
        self._thumbnail_extractor = thumbnail_extractor
        self._edit_service = edit_service

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
    def workingVideoRevision(self) -> int:
        """Monotonic revision for current working-video changes."""
        return self._session.working_video_revision

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

    @Property(list, notify=markersChanged)
    def markers(self) -> list[float]:
        """Cut markers as list of times in seconds."""
        return list(self._session.markers)

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
            old_markers = self._session.markers
            self._session.undo()
            self.videoChanged.emit()
            if self._session.markers != old_markers:
                self.markersChanged.emit()

    @Slot()
    def redo(self) -> None:
        """Redo the last undone edit."""
        if self._session.can_redo:
            old_markers = self._session.markers
            self._session.redo()
            self.videoChanged.emit()
            if self._session.markers != old_markers:
                self.markersChanged.emit()

    @Slot(float)
    def addMarker(self, time: float) -> None:
        """Add a cut marker at the specified time in seconds."""
        old_markers = self._session.markers
        self._session.add_marker(time)
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot(float)
    def removeMarker(self, time: float) -> None:
        """Remove the cut marker at the specified time."""
        old_markers = self._session.markers
        self._session.remove_marker(time)
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot()
    def clearMarkers(self) -> None:
        """Remove all cut markers."""
        old_markers = self._session.markers
        self._session.clear_markers()
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot(float, float)
    def moveMarker(self, old_time: float, new_time: float) -> None:
        """Move a marker from old_time to new_time."""
        old_markers = self._session.markers
        self._session.move_marker(old_time, new_time)
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot(int, int, int, int)
    def applyCrop(self, x: int, y: int, width: int, height: int) -> None:
        """Apply a crop operation to the working video."""
        if self._session.working_video is None:
            return
        request = CropRequest(x=x, y=y, width=width, height=height)
        result = self._edit_service.apply_crop(self._session.working_video, request)
        self._session.set_working_video(result.output_path)
        self.videoChanged.emit()

    @Slot(float, float)
    def applyCut(self, start: float, end: float) -> None:
        """Apply a cut (segment removal) to the working video."""
        if self._session.working_video is None:
            return
        request = CutRequest(start=start, end=end)
        result = self._edit_service.apply_cut(self._session.working_video, request)
        old_markers = self._session.markers
        self._session.apply_cut(start, end, result.output_path)
        self.videoChanged.emit()
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot(int, int, int)
    def requestThumbnails(self, frame_count: int, thumb_height: int, revision: int) -> None:
        """Request thumbnail extraction in a background thread.

        Args:
            frame_count: Number of frames to extract
            thumb_height: Height of each thumbnail in pixels
            revision: Working-video revision the request applies to
        """
        video_path = self._session.working_video
        current_revision = self._session.working_video_revision
        if video_path is None or frame_count <= 0 or revision != current_revision:
            return

        def extract_and_emit() -> None:
            frames = self._thumbnail_extractor.extract(video_path, frame_count, thumb_height)
            if revision != self._session.working_video_revision:
                return
            urls = [path.as_uri() for path in frames]
            # Emit signal (safe from thread via Qt's queued connections)
            self.thumbnailsReady.emit(urls)

        thread = threading.Thread(target=extract_and_emit, daemon=True)
        thread.start()
