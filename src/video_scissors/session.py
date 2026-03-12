"""Editor session model - core editing state container."""

from pathlib import Path


class EditorSession:
    """Manages the editing session state.

    Tracks the source video (original file) and working video
    (current state after edits). Source remains immutable while
    working video changes as edits are applied.
    """

    def __init__(self) -> None:
        self._source_video: Path | None = None
        self._working_video: Path | None = None

    @property
    def source_video(self) -> Path | None:
        """The original video file. Immutable after load."""
        return self._source_video

    @property
    def working_video(self) -> Path | None:
        """The current working video after edits."""
        return self._working_video

    @property
    def has_video(self) -> bool:
        """True if a video is loaded."""
        return self._source_video is not None

    def load(self, path: Path) -> None:
        """Load a video file, setting it as both source and working."""
        self._source_video = path
        self._working_video = path

    def set_working_video(self, path: Path) -> None:
        """Update the working video path after an edit."""
        self._working_video = path

    def close(self) -> None:
        """Close the session, clearing all state."""
        self._source_video = None
        self._working_video = None
