"""Editor session model - core editing state container."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

import av


@dataclass(frozen=True)
class Marker:
    """A cut marker with stable identity."""

    id: str
    time: float  # seconds

    @staticmethod
    def create(time: float) -> "Marker":
        """Create a new marker with a generated ID."""
        return Marker(id=uuid.uuid4().hex, time=time)


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
    markers: tuple[Marker, ...] = field(default_factory=tuple)


class EditorSession:
    """Manages the editing session state.

    Tracks the source video (original file) and working video
    (current state after edits). Source remains immutable while
    working video changes as edits are applied.

    Supports undo/redo via history stacks of session snapshots.
    Cut markers are first-class concepts that participate in undo/redo.
    """

    def __init__(self) -> None:
        self._source_video: Path | None = None
        self._current: SessionSnapshot | None = None
        self._undo_stack: list[SessionSnapshot] = []
        self._redo_stack: list[SessionSnapshot] = []
        self._working_video_revision: int = 0

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
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """True if there are undone edits that can be redone."""
        return len(self._redo_stack) > 0

    @property
    def markers(self) -> tuple[Marker, ...]:
        """Cut markers as sorted tuple by time."""
        if self._current is None:
            return ()
        return self._current.markers

    def load(self, path: Path) -> None:
        """Load a video file, setting it as both source and working."""
        self._source_video = path
        self._undo_stack.clear()
        self._redo_stack.clear()
        video_state = self._build_working_state(path)
        self._current = SessionSnapshot(video=video_state, markers=())
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

    def _push_undo(self) -> None:
        """Push current state to undo stack and clear redo."""
        if self._current is not None:
            self._undo_stack.append(self._current)
        self._redo_stack.clear()

    def set_working_video(self, path: Path) -> None:
        """Update the working video path after an edit."""
        self._push_undo()
        video_state = self._build_working_state(path)
        # Preserve current markers when video changes
        current_markers = self._current.markers if self._current else ()
        self._current = SessionSnapshot(video=video_state, markers=current_markers)
        self._bump_working_video_revision()

    def add_marker(self, time: float) -> Marker | None:
        """Add a cut marker at the specified time in seconds.

        Returns the created Marker, or None if duplicate time.
        """
        if self._current is None:
            return None
        # Check for duplicate time
        if any(m.time == time for m in self._current.markers):
            return None
        self._push_undo()
        marker = Marker.create(time)
        new_markers = tuple(sorted(self._current.markers + (marker,), key=lambda m: m.time))
        self._current = SessionSnapshot(video=self._current.video, markers=new_markers)
        return marker

    def remove_marker(self, marker_id: str) -> None:
        """Remove a cut marker by its ID."""
        if self._current is None:
            return
        if not any(m.id == marker_id for m in self._current.markers):
            return
        self._push_undo()
        new_markers = tuple(m for m in self._current.markers if m.id != marker_id)
        self._current = SessionSnapshot(video=self._current.video, markers=new_markers)

    def clear_markers(self) -> None:
        """Remove all cut markers."""
        if self._current is None or not self._current.markers:
            return
        self._push_undo()
        self._current = SessionSnapshot(video=self._current.video, markers=())

    def move_marker(self, marker_id: str, new_time: float) -> None:
        """Move a marker to a new time by its ID."""
        if self._current is None:
            return
        if not any(m.id == marker_id for m in self._current.markers):
            return
        self._push_undo()
        updated = (
            Marker(id=m.id, time=new_time) if m.id == marker_id else m
            for m in self._current.markers
        )
        new_markers = tuple(sorted(updated, key=lambda m: m.time))
        self._current = SessionSnapshot(video=self._current.video, markers=new_markers)

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

        cut_duration = end - start
        adjusted_markers: list[Marker] = []

        for marker in self._current.markers:
            if marker.time < start:
                # Before cut: unchanged
                adjusted_markers.append(marker)
            elif marker.time >= end:
                # After cut: shift earlier (preserve ID)
                adjusted_markers.append(Marker(id=marker.id, time=marker.time - cut_duration))
            # Inside cut [start, end): removed (not added)

        self._push_undo()
        video_state = self._build_working_state(output_path)
        self._current = SessionSnapshot(video=video_state, markers=tuple(adjusted_markers))
        self._bump_working_video_revision()

    def undo(self) -> None:
        """Undo the last edit, restoring the previous state."""
        if not self.can_undo or self._current is None:
            return
        self._redo_stack.append(self._current)
        self._current = self._undo_stack.pop()
        self._bump_working_video_revision()

    def redo(self) -> None:
        """Redo the last undone edit."""
        if not self.can_redo or self._current is None:
            return
        self._undo_stack.append(self._current)
        self._current = self._redo_stack.pop()
        self._bump_working_video_revision()

    def close(self) -> None:
        """Close the session, clearing all state."""
        had_video = self._source_video is not None or self._current is not None
        self._source_video = None
        self._current = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        if had_video:
            self._bump_working_video_revision()
