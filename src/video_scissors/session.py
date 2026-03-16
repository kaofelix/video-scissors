"""Editor session model - core editing state container."""

from dataclasses import dataclass, field
from pathlib import Path

import av
from PySide6.QtCore import QObject
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
    """Manages the editing session state.

    Tracks the source video (original file) and working video
    (current state after edits). Source remains immutable while
    working video changes as edits are applied.

    Supports undo/redo via history stacks of session snapshots.
    Cut markers are first-class concepts that participate in undo/redo.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source_video: Path | None = None
        self._current: SessionSnapshot | None = None
        self._qt_undo_stack = QUndoStack(self)
        self._working_video_revision: int = 0

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

    @property
    def has_video(self) -> bool:
        """True if a video is loaded."""
        return self._source_video is not None

    @property
    def video_width(self) -> int:
        """Width of the loaded video in pixels."""
        if self._current is None:
            return 0
        return self._current.video.width

    @property
    def video_height(self) -> int:
        """Height of the loaded video in pixels."""
        if self._current is None:
            return 0
        return self._current.video.height

    @property
    def video_frame_rate(self) -> float:
        """Frame rate of the loaded video in fps."""
        if self._current is None:
            return 0.0
        return self._current.video.frame_rate

    @property
    def working_video_revision(self) -> int:
        """Monotonic revision for working-video identity changes."""
        return self._working_video_revision

    @property
    def can_undo(self) -> bool:
        """True if there are edits that can be undone."""
        return self._qt_undo_stack.canUndo()

    @property
    def can_redo(self) -> bool:
        """True if there are undone edits that can be redone."""
        return self._qt_undo_stack.canRedo()

    @property
    def document(self) -> Document:
        """Current document (edit_spec + markers)."""
        if self._current is None:
            return Document()
        return self._current.document

    @property
    def markers(self) -> tuple[Marker, ...]:
        """Cut markers as sorted tuple by time."""
        return self.document.markers

    @property
    def source_duration(self) -> float:
        """Duration of source video in seconds."""
        if self._source_video is None:
            return 0.0
        return self._get_video_duration(self._source_video)

    @property
    def effective_duration(self) -> float:
        """Duration after cuts applied, in seconds."""
        return effective_duration(self.source_duration, self.document.edit_spec)

    def _get_video_duration(self, path: Path) -> float:
        """Get duration of a video file in seconds."""
        try:
            container = av.open(str(path))
            duration = float(container.duration) / av.time_base if container.duration else 0.0
            container.close()
            return duration
        except Exception:
            return 0.0

    def load(self, path: Path) -> None:
        """Load a video file, setting it as both source and working."""
        self._source_video = path
        self._qt_undo_stack.clear()
        video_state = self._build_working_state(path)
        self._current = SessionSnapshot(video=video_state, document=Document())
        self._bump_working_video_revision()

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
            # Frame rate from average_rate (Fraction), convert to float
            frame_rate = float(stream.average_rate) if stream.average_rate else 0.0
            container.close()
            return width, height, frame_rate
        except Exception:
            return 0, 0, 0.0

    def _bump_working_video_revision(self) -> None:
        """Advance the working-video revision after a state change."""
        self._working_video_revision += 1

    def _set_document(self, document: Document) -> None:
        """Update the document (called by commands)."""
        if self._current is None:
            return
        self._current = SessionSnapshot(video=self._current.video, document=document)

    def _restore_snapshot(self, snapshot: SessionSnapshot) -> None:
        """Restore a complete snapshot (called by SetWorkingVideoCommand)."""
        self._current = snapshot
        self._bump_working_video_revision()

    def set_working_video(self, path: Path) -> None:
        """Update the working video path after an edit."""
        if self._current is None:
            return
        previous_snapshot = self._current
        video_state = self._build_working_state(path)
        # Preserve current document when video changes
        new_snapshot = SessionSnapshot(video=video_state, document=self._current.document)
        # Use QUndoStack for proper ordering
        cmd = SetWorkingVideoCommand(self, previous_snapshot, new_snapshot)
        self._qt_undo_stack.push(cmd)

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

    def add_marker(self, time: float) -> Marker | None:
        """Add a cut marker at the specified time in seconds.

        Returns the created Marker, or None if duplicate time.
        """
        if self._current is None:
            return None
        # Check for duplicate time
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

    def apply_cut(self, start: float, end: float, output_path: Path) -> None:
        """Apply a cut and adjust markers accordingly.

        Markers inside [start, end) are removed.
        Markers after end are shifted earlier by (end - start).
        Markers before start are unchanged.

        Args:
            start: Start time of cut region in seconds
            end: End time of cut region in seconds
            output_path: Path to the cut video file
        """
        if self._current is None:
            return

        previous_snapshot = self._current
        cut_duration = end - start
        adjusted_markers: list[Marker] = []

        for marker in self._current.document.markers:
            if marker.time < start:
                # Before cut: unchanged
                adjusted_markers.append(marker)
            elif marker.time >= end:
                # After cut: shift earlier (preserve ID)
                adjusted_markers.append(Marker(id=marker.id, time=marker.time - cut_duration))
            # Inside cut [start, end): removed (not added)

        video_state = self._build_working_state(output_path)
        current_edit_spec = self._current.document.edit_spec
        new_document = Document(
            edit_spec=current_edit_spec,
            markers=tuple(adjusted_markers),
        )
        new_snapshot = SessionSnapshot(
            video=video_state,
            document=new_document,
        )
        # Use QUndoStack for proper ordering
        cmd = SetWorkingVideoCommand(self, previous_snapshot, new_snapshot)
        self._qt_undo_stack.push(cmd)

    def undo(self) -> None:
        """Undo the last edit, restoring the previous state."""
        if not self.can_undo or self._current is None:
            return
        self._qt_undo_stack.undo()

    def redo(self) -> None:
        """Redo the last undone edit."""
        if not self.can_redo or self._current is None:
            return
        self._qt_undo_stack.redo()

    def close(self) -> None:
        """Close the session, clearing all state."""
        had_video = self._source_video is not None or self._current is not None
        self._source_video = None
        self._current = None
        self._qt_undo_stack.clear()
        if had_video:
            self._bump_working_video_revision()
