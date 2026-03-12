"""Editor session model - core editing state container."""

from pathlib import Path

import av


class EditorSession:
    """Manages the editing session state.

    Tracks the source video (original file) and working video
    (current state after edits). Source remains immutable while
    working video changes as edits are applied.
    """

    def __init__(self) -> None:
        self._source_video: Path | None = None
        self._working_video: Path | None = None
        self._video_width: int = 0
        self._video_height: int = 0

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

    @property
    def video_width(self) -> int:
        """Width of the loaded video in pixels."""
        return self._video_width

    @property
    def video_height(self) -> int:
        """Height of the loaded video in pixels."""
        return self._video_height

    def load(self, path: Path) -> None:
        """Load a video file, setting it as both source and working."""
        self._source_video = path
        self._working_video = path
        self._probe_dimensions(path)

    def _probe_dimensions(self, path: Path) -> None:
        """Probe video file to get dimensions."""
        try:
            container = av.open(str(path))
            stream = container.streams.video[0]
            self._video_width = stream.width
            self._video_height = stream.height
            container.close()
        except Exception:
            self._video_width = 0
            self._video_height = 0

    def set_working_video(self, path: Path) -> None:
        """Update the working video path after an edit."""
        self._working_video = path

    def close(self) -> None:
        """Close the session, clearing all state."""
        self._source_video = None
        self._working_video = None
        self._video_width = 0
        self._video_height = 0
