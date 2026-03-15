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
        self._suggested_position_ms: float = 0

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

    @Property(float, notify=videoChanged)
    def videoFrameRate(self) -> float:
        """Frame rate of the loaded video in fps."""
        return self._session.video_frame_rate

    @Property(bool, notify=videoChanged)
    def canUndo(self) -> bool:
        """True if there are edits that can be undone."""
        return self._session.can_undo

    @Property(bool, notify=videoChanged)
    def canRedo(self) -> bool:
        """True if there are undone edits that can be redone."""
        return self._session.can_redo

    @Property(list, notify=markersChanged)
    def markers(self) -> list[dict]:
        """Cut markers as list of {id, time} objects for QML."""
        return [{"id": m.id, "time": m.time} for m in self._session.markers]

    @Property(float, notify=videoChanged)
    def suggestedPositionMs(self) -> float:
        """Suggested playhead position in milliseconds after an operation."""
        return self._suggested_position_ms

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

    @Slot(float)
    def undo(self, currentPositionMs: float = 0) -> None:
        """Undo the last edit."""
        if self._session.can_undo:
            old_markers = self._session.markers
            self._session.undo()
            self._suggested_position_ms = currentPositionMs
            self.videoChanged.emit()
            if self._session.markers != old_markers:
                self.markersChanged.emit()

    @Slot(float)
    def redo(self, currentPositionMs: float = 0) -> None:
        """Redo the last undone edit."""
        if self._session.can_redo:
            old_markers = self._session.markers
            self._session.redo()
            self._suggested_position_ms = currentPositionMs
            self.videoChanged.emit()
            if self._session.markers != old_markers:
                self.markersChanged.emit()

    @Slot(float, result="QVariant")
    def addMarker(self, time: float) -> dict | None:
        """Add a cut marker at the specified time in seconds.

        Returns the created marker {id, time} or None if duplicate.
        """
        marker = self._session.add_marker(time)
        if marker is not None:
            self.markersChanged.emit()
            return {"id": marker.id, "time": marker.time}
        return None

    @Slot(str)
    def removeMarker(self, marker_id: str) -> None:
        """Remove the cut marker by its ID."""
        old_markers = self._session.markers
        self._session.remove_marker(marker_id)
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot()
    def clearMarkers(self) -> None:
        """Remove all cut markers."""
        old_markers = self._session.markers
        self._session.clear_markers()
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot(str, float)
    def moveMarker(self, marker_id: str, new_time: float) -> None:
        """Move a marker to a new time by its ID."""
        old_markers = self._session.markers
        self._session.move_marker(marker_id, new_time)
        if self._session.markers != old_markers:
            self.markersChanged.emit()

    @Slot(int, int, int, int, float)
    def applyCrop(
        self, x: int, y: int, width: int, height: int, currentPositionMs: float = 0
    ) -> None:
        """Apply a crop operation to the working video."""
        if self._session.working_video is None:
            return
        request = CropRequest(x=x, y=y, width=width, height=height)
        result = self._edit_service.apply_crop(self._session.working_video, request)
        self._session.set_working_video(result.output_path)
        self._suggested_position_ms = currentPositionMs
        self.videoChanged.emit()

    @Slot(float, float, float)
    def applyCut(self, start: float, end: float, currentPositionMs: float = 0) -> None:
        """Apply a cut (segment removal) to the working video."""
        if self._session.working_video is None:
            return
        request = CutRequest(start=start, end=end)
        result = self._edit_service.apply_cut(self._session.working_video, request)
        old_markers = self._session.markers
        self._session.apply_cut(start, end, result.output_path)
        # Adjust position based on cut region (start/end are in seconds, position in ms)
        start_ms = start * 1000
        end_ms = end * 1000
        cut_duration_ms = end_ms - start_ms
        if currentPositionMs < start_ms:
            # Before cut: unchanged
            self._suggested_position_ms = currentPositionMs
        elif currentPositionMs < end_ms:
            # Inside cut: snap to cut start
            self._suggested_position_ms = start_ms
        else:
            # After cut: shift by cut duration
            self._suggested_position_ms = currentPositionMs - cut_duration_ms
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
