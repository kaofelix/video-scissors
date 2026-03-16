"""Editor session model - core editing state container and QML interface.

The EditorSession is the top-level QObject exposed to QML. It owns the
editing state, coordinates services, and provides per-property notify
signals for fine-grained QML binding updates.

QML accesses the session directly:
    session.hasVideo
    session.document.editSpec.hasCrop
    session.displayWidth
"""

import threading
from dataclasses import dataclass, field
from pathlib import Path

import av
from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QUndoStack

from video_scissors.commands import (
    AddCutCommand,
    AddMarkerCommand,
    ClearMarkersCommand,
    MoveMarkerCommand,
    RemoveMarkerCommand,
    SetCropCommand,
    SetWorkingVideoCommand,
)
from video_scissors.document import Document, Marker, effective_duration
from video_scissors.document import effective_to_source as _effective_to_source
from video_scissors.document import source_to_effective as _source_to_effective
from video_scissors.models import DocumentModel
from video_scissors.services import CropRequest, CutRequest, EditService, ThumbnailExtractorProtocol


@dataclass(frozen=True)
class WorkingVideoState:
    """Snapshot of the current working video."""

    path: Path
    width: int
    height: int
    frame_rate: float


@dataclass(frozen=True)
class SessionSnapshot:
    """Complete session state snapshot for undo/redo."""

    video: WorkingVideoState
    document: Document = field(default_factory=Document)


class EditorSession(QObject):
    """Manages the editing session state and provides QML interface.

    This is the root QObject exposed to QML as the context property "session".
    Properties use per-property notify signals (no artificial signal groups).

    Domain sub-objects are accessible through the object graph:
        session.document          → DocumentModel
        session.document.editSpec → EditSpecModel
    """

    # Per-property signals
    hasVideoChanged = Signal()
    workingVideoUrlChanged = Signal()
    workingVideoRevisionChanged = Signal()
    videoWidthChanged = Signal()
    videoHeightChanged = Signal()
    videoFrameRateChanged = Signal()
    displayWidthChanged = Signal()
    displayHeightChanged = Signal()
    effectiveDurationMsChanged = Signal()
    contentRevisionChanged = Signal()
    suggestedPositionMsChanged = Signal()

    # Forwarded from QUndoStack
    undoStateChanged = Signal()

    # Thumbnail results (event, not a property signal)
    thumbnailsReady = Signal(list)

    def __init__(
        self,
        thumbnail_extractor: ThumbnailExtractorProtocol | None = None,
        edit_service: EditService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._source_video: Path | None = None
        self._current: SessionSnapshot | None = None
        self._qt_undo_stack = QUndoStack(self)
        self._working_video_revision: int = 0
        self._content_revision: int = 0
        self._suggested_position_ms: float = 0
        self._thumbnail_extractor = thumbnail_extractor
        self._edit_service = edit_service

        # Stable sub-models for QML binding
        self._document_model = DocumentModel(self)

        # Connect QUndoStack signals for canUndo/canRedo
        self._qt_undo_stack.canUndoChanged.connect(self.undoStateChanged)
        self._qt_undo_stack.canRedoChanged.connect(self.undoStateChanged)

        # Derived property dependencies:
        # display dimensions depend on crop + video
        self._document_model._edit_spec_model.cropChanged.connect(self._emit_display_dimensions)
        # content revision tracks all thumbnail-invalidating changes
        self._document_model._edit_spec_model.cutsChanged.connect(self._bump_content_revision)
        self._document_model._edit_spec_model.cropChanged.connect(self._bump_content_revision)
        # effective duration depends on cuts
        self._document_model._edit_spec_model.cutsChanged.connect(self.effectiveDurationMsChanged)

    # ------------------------------------------------------------------ #
    #  Qt Properties (QML interface)                                      #
    # ------------------------------------------------------------------ #

    @property
    def undo_stack(self) -> QUndoStack:
        """Qt undo stack for undo/redo signals and actions."""
        return self._qt_undo_stack

    @property
    def source_video(self) -> Path | None:
        """The original video file. Immutable after load."""
        return self._source_video

    @property
    def working_video(self) -> Path | None:
        """The current working video after edits."""
        if self._current is None:
            return None
        return self._current.video.path

    @Property(bool, notify=hasVideoChanged)
    def hasVideo(self) -> bool:
        """True if a video is loaded."""
        return self._source_video is not None

    # Keep the Python-style alias
    @property
    def has_video(self) -> bool:
        return self._source_video is not None

    @Property(str, notify=workingVideoUrlChanged)
    def workingVideoUrl(self) -> str:
        """The working video as a file:// URL for QML."""
        if self._current is None:
            return ""
        return self._current.video.path.as_uri()

    @Property(int, notify=workingVideoRevisionChanged)
    def workingVideoRevision(self) -> int:
        """Monotonic revision for working-video identity changes."""
        return self._working_video_revision

    # Python-style alias
    @property
    def working_video_revision(self) -> int:
        return self._working_video_revision

    @Property(int, notify=videoWidthChanged)
    def videoWidth(self) -> int:
        """Width of the loaded video in pixels."""
        if self._current is None:
            return 0
        return self._current.video.width

    # Python-style alias
    @property
    def video_width(self) -> int:
        if self._current is None:
            return 0
        return self._current.video.width

    @Property(int, notify=videoHeightChanged)
    def videoHeight(self) -> int:
        """Height of the loaded video in pixels."""
        if self._current is None:
            return 0
        return self._current.video.height

    # Python-style alias
    @property
    def video_height(self) -> int:
        if self._current is None:
            return 0
        return self._current.video.height

    @Property(float, notify=videoFrameRateChanged)
    def videoFrameRate(self) -> float:
        """Frame rate of the loaded video in fps."""
        if self._current is None:
            return 0.0
        return self._current.video.frame_rate

    # Python-style alias
    @property
    def video_frame_rate(self) -> float:
        if self._current is None:
            return 0.0
        return self._current.video.frame_rate

    @Property(bool, notify=undoStateChanged)
    def canUndo(self) -> bool:
        """True if there are edits that can be undone."""
        return self._qt_undo_stack.canUndo()

    # Python-style alias
    @property
    def can_undo(self) -> bool:
        return self._qt_undo_stack.canUndo()

    @Property(bool, notify=undoStateChanged)
    def canRedo(self) -> bool:
        """True if there are undone edits that can be redone."""
        return self._qt_undo_stack.canRedo()

    # Python-style alias
    @property
    def can_redo(self) -> bool:
        return self._qt_undo_stack.canRedo()

    @Property(QObject, constant=True)
    def document(self) -> DocumentModel:
        """The document sub-model (stable QObject identity for QML)."""
        return self._document_model

    @Property(int, notify=displayWidthChanged)
    def displayWidth(self) -> int:
        """Width for display: crop width if cropped, source width otherwise."""
        crop = self._raw_document.edit_spec.crop
        if crop is not None:
            return crop.width
        return self.video_width

    @Property(int, notify=displayHeightChanged)
    def displayHeight(self) -> int:
        """Height for display: crop height if cropped, source height otherwise."""
        crop = self._raw_document.edit_spec.crop
        if crop is not None:
            return crop.height
        return self.video_height

    @Property(float, notify=effectiveDurationMsChanged)
    def effectiveDurationMs(self) -> float:
        """Duration after cuts applied, in milliseconds."""
        return self.effective_duration * 1000

    @Property(int, notify=contentRevisionChanged)
    def contentRevision(self) -> int:
        """Revision counter for thumbnail invalidation.

        Increments on file open, close, and edit spec changes.
        """
        return self._content_revision

    @Property(float, notify=suggestedPositionMsChanged)
    def suggestedPositionMs(self) -> float:
        """Suggested playhead position in milliseconds after an operation."""
        return self._suggested_position_ms

    # ------------------------------------------------------------------ #
    #  Internal read-only properties                                      #
    # ------------------------------------------------------------------ #

    @property
    def _raw_document(self) -> Document:
        """Current frozen document (for internal use and commands)."""
        if self._current is None:
            return Document()
        return self._current.document

    # Public alias used by test_session.py and commands
    @property
    def markers(self) -> tuple[Marker, ...]:
        """Cut markers as sorted tuple by time."""
        return self._raw_document.markers

    @property
    def source_duration(self) -> float:
        """Duration of source video in seconds."""
        if self._source_video is None:
            return 0.0
        return self._get_video_duration(self._source_video)

    @property
    def effective_duration(self) -> float:
        """Duration after cuts applied, in seconds."""
        return effective_duration(self.source_duration, self._raw_document.edit_spec)

    # ------------------------------------------------------------------ #
    #  QML Slots                                                          #
    # ------------------------------------------------------------------ #

    @Slot(float, result=float)
    def sourceToEffective(self, source_ms: float) -> float:
        """Convert source time (ms) to effective time (ms) for display."""
        source_s = source_ms / 1000
        effective_s = _source_to_effective(source_s, self._raw_document.edit_spec)
        return effective_s * 1000

    @Slot(float, result=float)
    def effectiveToSource(self, effective_ms: float) -> float:
        """Convert effective time (ms) to source time (ms) for seeking/cuts."""
        effective_s = effective_ms / 1000
        source_s = _effective_to_source(effective_s, self._raw_document.edit_spec)
        return source_s * 1000

    @Slot(str)
    def openFile(self, path: str) -> None:
        """Open a video file (QML slot)."""
        self.load(Path(path))

    @Slot()
    def closeSession(self) -> None:
        """Close the current session (QML slot)."""
        self.close()

    @Slot(float)
    def undo(self, currentPositionMs: float = 0) -> None:
        """Undo the last edit."""
        if not self._qt_undo_stack.canUndo() or self._current is None:
            return
        old_video = self.working_video
        old_doc = self._raw_document
        self._qt_undo_stack.undo()
        self._suggested_position_ms = currentPositionMs
        self.suggestedPositionMsChanged.emit()
        if self.working_video != old_video:
            self._emit_video_properties()
        self._sync_document_model()
        if old_doc.edit_spec != self._raw_document.edit_spec:
            self._emit_display_dimensions()

    @Slot(float)
    def redo(self, currentPositionMs: float = 0) -> None:
        """Redo the last undone edit."""
        if not self._qt_undo_stack.canRedo() or self._current is None:
            return
        old_video = self.working_video
        old_doc = self._raw_document
        self._qt_undo_stack.redo()
        self._suggested_position_ms = currentPositionMs
        self.suggestedPositionMsChanged.emit()
        if self.working_video != old_video:
            self._emit_video_properties()
        self._sync_document_model()
        if old_doc.edit_spec != self._raw_document.edit_spec:
            self._emit_display_dimensions()

    @Slot(float, result="QVariant")
    def addMarker(self, time: float) -> dict | None:
        """Add a cut marker (QML slot). Returns {id, time} or None."""
        marker = self.add_marker(time)
        if marker is not None:
            self._sync_document_model()
            return {"id": marker.id, "time": marker.time}
        return None

    @Slot(str)
    def removeMarker(self, marker_id: str) -> None:
        """Remove a cut marker by ID (QML slot)."""
        old_markers = self.markers
        self.remove_marker(marker_id)
        if self.markers != old_markers:
            self._sync_document_model()

    @Slot()
    def clearMarkers(self) -> None:
        """Remove all cut markers (QML slot)."""
        old_markers = self.markers
        self.clear_markers()
        if self.markers != old_markers:
            self._sync_document_model()

    @Slot(str, float)
    def moveMarker(self, marker_id: str, new_time: float) -> None:
        """Move a marker to a new time (QML slot)."""
        old_markers = self.markers
        self.move_marker(marker_id, new_time)
        if self.markers != old_markers:
            self._sync_document_model()

    @Slot(float, float)
    def addCut(self, start: float, end: float) -> None:
        """Add a cut region (QML slot). Times in seconds."""
        self.add_cut(start, end)
        self._sync_document_model()

    @Slot(int, int, int, int)
    def setCrop(self, x: int, y: int, width: int, height: int) -> None:
        """Set crop region (QML slot). Coordinates in source pixels."""
        self.set_crop(x, y, width, height)
        self._sync_document_model()

    @Slot(int, int, int, int, float)
    def applyCrop(
        self, x: int, y: int, width: int, height: int, currentPositionMs: float = 0
    ) -> None:
        """Apply a crop operation to the working video."""
        if self._current is None or self._edit_service is None:
            return
        request = CropRequest(x=x, y=y, width=width, height=height)
        result = self._edit_service.apply_crop(self._current.video.path, request)
        self.set_working_video(result.output_path)
        self._suggested_position_ms = currentPositionMs
        self.suggestedPositionMsChanged.emit()

    @Slot(float, float, float)
    def applyCut(self, start: float, end: float, currentPositionMs: float = 0) -> None:
        """Apply a cut (segment removal) to the working video."""
        if self._current is None or self._edit_service is None:
            return
        request = CutRequest(start=start, end=end)
        result = self._edit_service.apply_cut(self._current.video.path, request)
        self.apply_cut(start, end, result.output_path)
        # Adjust position based on cut region
        start_ms = start * 1000
        end_ms = end * 1000
        cut_duration_ms = end_ms - start_ms
        if currentPositionMs < start_ms:
            self._suggested_position_ms = currentPositionMs
        elif currentPositionMs < end_ms:
            self._suggested_position_ms = start_ms
        else:
            self._suggested_position_ms = currentPositionMs - cut_duration_ms
        self.suggestedPositionMsChanged.emit()

    @Slot(int, int, int)
    def requestThumbnails(self, frame_count: int, thumb_height: int, revision: int) -> None:
        """Request thumbnail extraction in a background thread."""
        if self._thumbnail_extractor is None:
            return
        video_path = self.working_video
        if video_path is None or frame_count <= 0 or revision != self._content_revision:
            return

        crop = self._raw_document.edit_spec.crop
        extractor = self._thumbnail_extractor
        content_revision = self._content_revision

        def extract_and_emit() -> None:
            frames = extractor.extract(video_path, frame_count, thumb_height, crop=crop)
            if revision != content_revision:
                return
            urls = [path.as_uri() for path in frames]
            self.thumbnailsReady.emit(urls)

        thread = threading.Thread(target=extract_and_emit, daemon=True)
        thread.start()

    # ------------------------------------------------------------------ #
    #  Internal Python API (used by commands and tests)                   #
    # ------------------------------------------------------------------ #

    def load(self, path: Path) -> None:
        """Load a video file, setting it as both source and working."""
        self._source_video = path
        self._qt_undo_stack.clear()
        video_state = self._build_working_state(path)
        self._current = SessionSnapshot(video=video_state, document=Document())
        self._bump_working_video_revision()
        self._sync_document_model()
        self._emit_all_video_properties()
        self._bump_content_revision()

    def close(self) -> None:
        """Close the session, clearing all state."""
        had_video = self._source_video is not None or self._current is not None
        self._source_video = None
        self._current = None
        self._qt_undo_stack.clear()
        self._sync_document_model()
        if had_video:
            self._bump_working_video_revision()
            self._emit_all_video_properties()
            self._bump_content_revision()

    def set_working_video(self, path: Path) -> None:
        """Update the working video path after an edit."""
        if self._current is None:
            return
        previous_snapshot = self._current
        video_state = self._build_working_state(path)
        new_snapshot = SessionSnapshot(video=video_state, document=self._current.document)
        cmd = SetWorkingVideoCommand(self, previous_snapshot, new_snapshot)
        self._qt_undo_stack.push(cmd)
        self._emit_video_properties()

    def add_marker(self, time: float) -> Marker | None:
        """Add a cut marker at the specified time in seconds.

        Returns the created Marker, or None if duplicate time.
        """
        if self._current is None:
            return None
        if any(m.time == time for m in self._current.document.markers):
            return None
        marker = Marker.create(time)
        self._qt_undo_stack.push(AddMarkerCommand(self, marker))
        return marker

    def remove_marker(self, marker_id: str) -> None:
        """Remove a cut marker by its ID."""
        if self._current is None:
            return
        marker = next((m for m in self._current.document.markers if m.id == marker_id), None)
        if marker is None:
            return
        self._qt_undo_stack.push(RemoveMarkerCommand(self, marker))

    def clear_markers(self) -> None:
        """Remove all cut markers."""
        if self._current is None or not self._current.document.markers:
            return
        markers = self._current.document.markers
        self._qt_undo_stack.push(ClearMarkersCommand(self, markers))

    def move_marker(self, marker_id: str, new_time: float) -> None:
        """Move a marker to a new time by its ID."""
        if self._current is None:
            return
        marker = next((m for m in self._current.document.markers if m.id == marker_id), None)
        if marker is None:
            return
        self._qt_undo_stack.push(MoveMarkerCommand(self, marker_id, marker.time, new_time))

    def add_cut(self, start: float, end: float) -> None:
        """Add a cut region (non-destructive). Times in source coordinates."""
        if self._current is None:
            return
        self._qt_undo_stack.push(AddCutCommand(self, start, end))

    def set_crop(self, x: int, y: int, width: int, height: int) -> None:
        """Set crop region (non-destructive). Coordinates in source pixels."""
        if self._current is None:
            return
        self._qt_undo_stack.push(SetCropCommand(self, x, y, width, height))

    def apply_cut(self, start: float, end: float, output_path: Path) -> None:
        """Apply a cut and adjust markers accordingly.

        Markers inside [start, end) are removed.
        Markers after end are shifted earlier by (end - start).
        """
        if self._current is None:
            return

        previous_snapshot = self._current
        cut_duration = end - start
        adjusted_markers: list[Marker] = []

        for marker in self._current.document.markers:
            if marker.time < start:
                adjusted_markers.append(marker)
            elif marker.time >= end:
                adjusted_markers.append(Marker(id=marker.id, time=marker.time - cut_duration))

        video_state = self._build_working_state(output_path)
        current_edit_spec = self._current.document.edit_spec
        new_document = Document(
            edit_spec=current_edit_spec,
            markers=tuple(adjusted_markers),
        )
        new_snapshot = SessionSnapshot(video=video_state, document=new_document)
        cmd = SetWorkingVideoCommand(self, previous_snapshot, new_snapshot)
        self._qt_undo_stack.push(cmd)
        self._emit_video_properties()
        self._sync_document_model()

    def _set_document(self, document: Document) -> None:
        """Update the document (called by commands)."""
        if self._current is None:
            return
        self._current = SessionSnapshot(video=self._current.video, document=document)

    def _restore_snapshot(self, snapshot: SessionSnapshot) -> None:
        """Restore a complete snapshot (called by SetWorkingVideoCommand)."""
        self._current = snapshot
        self._bump_working_video_revision()

    # ------------------------------------------------------------------ #
    #  Signal emission helpers                                            #
    # ------------------------------------------------------------------ #

    def _sync_document_model(self) -> None:
        """Sync the QML document model with the current frozen document."""
        self._document_model._update(self._raw_document)

    def _emit_video_properties(self) -> None:
        """Emit signals for all video-related properties."""
        self.hasVideoChanged.emit()
        self.workingVideoUrlChanged.emit()
        self.workingVideoRevisionChanged.emit()
        self.videoWidthChanged.emit()
        self.videoHeightChanged.emit()
        self.videoFrameRateChanged.emit()

    def _emit_all_video_properties(self) -> None:
        """Emit signals for all video properties including derived."""
        self._emit_video_properties()
        self._emit_display_dimensions()
        self.effectiveDurationMsChanged.emit()

    def _emit_display_dimensions(self) -> None:
        """Emit display dimension signals (derived from video + crop)."""
        self.displayWidthChanged.emit()
        self.displayHeightChanged.emit()

    def _bump_content_revision(self) -> None:
        """Increment content revision and emit signal."""
        self._content_revision += 1
        self.contentRevisionChanged.emit()

    def _bump_working_video_revision(self) -> None:
        """Advance the working-video revision after a state change."""
        self._working_video_revision += 1

    # ------------------------------------------------------------------ #
    #  Video file utilities                                               #
    # ------------------------------------------------------------------ #

    def _get_video_duration(self, path: Path) -> float:
        """Get duration of a video file in seconds."""
        try:
            container = av.open(str(path))
            duration = float(container.duration) / av.time_base if container.duration else 0.0
            container.close()
            return duration
        except Exception:
            return 0.0

    def _build_working_state(self, path: Path) -> WorkingVideoState:
        """Build a working-video snapshot from a file path."""
        width, height, frame_rate = self._probe_video_metadata(path)
        return WorkingVideoState(path=path, width=width, height=height, frame_rate=frame_rate)

    def _probe_video_metadata(self, path: Path) -> tuple[int, int, float]:
        """Probe video file to get dimensions and frame rate."""
        try:
            container = av.open(str(path))
            stream = container.streams.video[0]
            width = stream.width
            height = stream.height
            frame_rate = float(stream.average_rate) if stream.average_rate else 0.0
            container.close()
            return width, height, frame_rate
        except Exception:
            return 0, 0, 0.0
