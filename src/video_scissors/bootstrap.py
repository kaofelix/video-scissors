"""Application/service composition helpers."""

import tempfile
from pathlib import Path

from PySide6.QtCore import QObject

from video_scissors.export_service import FFmpegExportService
from video_scissors.session import EditorSession
from video_scissors.thumbnails import ThumbnailExtractor


def create_session(
    parent: QObject | None = None,
    workspace_dir: Path | None = None,
    thumbnail_extractor: ThumbnailExtractor | None = None,
) -> EditorSession:
    """Compose an EditorSession with default concrete services.

    Service and workspace construction live here at the application
    composition boundary.
    """
    workspace_dir = workspace_dir or Path(tempfile.mkdtemp(prefix="video_scissors_"))

    if thumbnail_extractor is None:
        thumbnail_dir = workspace_dir / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)
        thumbnail_extractor = ThumbnailExtractor(cache_dir=thumbnail_dir)

    return EditorSession(
        thumbnail_extractor=thumbnail_extractor,
        export_service=FFmpegExportService(),
        parent=parent,
    )
