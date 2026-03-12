"""Editor session model - core editing state container."""

from dataclasses import dataclass
from pathlib import Path

import av


@dataclass(frozen=True)
class WorkingVideoState:
    """Snapshot of the current working video."""

    path: Path
    width: int
    height: int


class EditorSession:
    """Manages the editing session state.

    Tracks the source video (original file) and working video
    (current state after edits). Source remains immutable while
    working video changes as edits are applied.

    Supports undo/redo via history stacks of working video snapshots.
    """

    def __init__(self) -> None:
        self._source_video: Path | None = None
        self._working_state: WorkingVideoState | None = None
        self._undo_stack: list[WorkingVideoState] = []
        self._redo_stack: list[WorkingVideoState] = []
        self._working_video_revision: int = 0

    @property
    def source_video(self) -> Path | None:
        """The original video file. Immutable after load."""
        return self._source_video

    @property
    def working_video(self) -> Path | None:
        """The current working video after edits."""
        if self._working_state is None:
            return None
        return self._working_state.path

    @property
    def has_video(self) -> bool:
        """True if a video is loaded."""
        return self._source_video is not None

    @property
    def video_width(self) -> int:
        """Width of the loaded video in pixels."""
        if self._working_state is None:
            return 0
        return self._working_state.width

    @property
    def video_height(self) -> int:
        """Height of the loaded video in pixels."""
        if self._working_state is None:
            return 0
        return self._working_state.height

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

    def load(self, path: Path) -> None:
        """Load a video file, setting it as both source and working."""
        self._source_video = path
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._working_state = self._build_working_state(path)
        self._bump_working_video_revision()

    def _build_working_state(self, path: Path) -> WorkingVideoState:
        """Build a working-video snapshot from a file path."""
        width, height = self._probe_dimensions(path)
        return WorkingVideoState(path=path, width=width, height=height)

    def _probe_dimensions(self, path: Path) -> tuple[int, int]:
        """Probe video file to get dimensions."""
        try:
            container = av.open(str(path))
            stream = container.streams.video[0]
            width = stream.width
            height = stream.height
            container.close()
            return width, height
        except Exception:
            return 0, 0

    def _bump_working_video_revision(self) -> None:
        """Advance the working-video revision after a state change."""
        self._working_video_revision += 1

    def set_working_video(self, path: Path) -> None:
        """Update the working video path after an edit."""
        if self._working_state is not None:
            self._undo_stack.append(self._working_state)
        self._redo_stack.clear()
        self._working_state = self._build_working_state(path)
        self._bump_working_video_revision()

    def undo(self) -> None:
        """Undo the last edit, restoring the previous working video."""
        if not self.can_undo or self._working_state is None:
            return
        self._redo_stack.append(self._working_state)
        self._working_state = self._undo_stack.pop()
        self._bump_working_video_revision()

    def redo(self) -> None:
        """Redo the last undone edit."""
        if not self.can_redo or self._working_state is None:
            return
        self._undo_stack.append(self._working_state)
        self._working_state = self._redo_stack.pop()
        self._bump_working_video_revision()

    def close(self) -> None:
        """Close the session, clearing all state."""
        had_video = self._source_video is not None or self._working_state is not None
        self._source_video = None
        self._working_state = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        if had_video:
            self._bump_working_video_revision()
