"""Application/service composition helpers."""

import tempfile
from pathlib import Path

from PySide6.QtCore import QObject

from video_scissors.bridge import SessionBridge
from video_scissors.edit_service import FFmpegEditService
from video_scissors.services import EditService
from video_scissors.session import EditorSession
from video_scissors.thumbnails import ThumbnailExtractor


def create_session_bridge(
    session: EditorSession,
    parent: QObject | None = None,
    workspace_dir: Path | None = None,
    thumbnail_extractor: ThumbnailExtractor | None = None,
    edit_service: EditService | None = None,
) -> SessionBridge:
    """Compose a SessionBridge with default concrete services.

    The bridge itself stays focused on adapting/delegating; service and workspace
    construction live here at the application composition boundary.
    """
    workspace_dir = workspace_dir or Path(tempfile.mkdtemp(prefix="video_scissors_"))

    if thumbnail_extractor is None:
        thumbnail_dir = workspace_dir / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)
        thumbnail_extractor = ThumbnailExtractor(cache_dir=thumbnail_dir)

    if edit_service is None:
        edit_dir = workspace_dir / "edits"
        edit_dir.mkdir(exist_ok=True)
        edit_service = FFmpegEditService(output_dir=edit_dir)

    return SessionBridge(
        session,
        parent=parent,
        thumbnail_extractor=thumbnail_extractor,
        edit_service=edit_service,
    )
