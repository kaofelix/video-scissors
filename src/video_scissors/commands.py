"""Command-based undo architecture using Qt's QUndoStack.

Commands are QUndoCommand subclasses that operate on the session's document.
Each command captures state before execution and restores it on undo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

from video_scissors.document import CropRect, Document, EditSpec, Marker

if TYPE_CHECKING:
    from video_scissors.session import EditorSession, SessionSnapshot


class SetWorkingVideoCommand(QUndoCommand):
    """Set working video path (for destructive edits that produce new files).

    This is a legacy command for backward compatibility with operations that
    produce new video files (crops, destructive cuts). Eventually these will
    be replaced with non-destructive edits.
    """

    def __init__(
        self,
        session: EditorSession,
        previous_snapshot: SessionSnapshot,
        new_snapshot: SessionSnapshot,
        parent: QUndoCommand | None = None,
    ):
        super().__init__("Video edit", parent)
        self._session = session
        self._previous_snapshot = previous_snapshot
        self._new_snapshot = new_snapshot

    def redo(self) -> None:
        """Apply the new working video."""
        self._session._restore_snapshot(self._new_snapshot)

    def undo(self) -> None:
        """Restore the previous working video."""
        self._session._restore_snapshot(self._previous_snapshot)


class AddCutCommand(QUndoCommand):
    """Add a cut region to the edit spec."""

    def __init__(
        self, session: EditorSession, start: float, end: float, parent: QUndoCommand | None = None
    ):
        super().__init__(f"Cut {start:.1f}s - {end:.1f}s", parent)
        self._session = session
        self._start = start
        self._end = end
        self._previous_spec: EditSpec | None = None

    def redo(self) -> None:
        """Add the cut to the document."""
        self._previous_spec = self._session.document.edit_spec
        new_spec = self._previous_spec.with_cut(self._start, self._end)
        self._session._set_document(
            Document(edit_spec=new_spec, markers=self._session.document.markers)
        )

    def undo(self) -> None:
        """Restore the previous edit spec."""
        if self._previous_spec is not None:
            self._session._set_document(
                Document(edit_spec=self._previous_spec, markers=self._session.document.markers)
            )


class SetCropCommand(QUndoCommand):
    """Set crop region on the edit spec."""

    def __init__(
        self,
        session: EditorSession,
        x: int,
        y: int,
        width: int,
        height: int,
        parent: QUndoCommand | None = None,
    ):
        super().__init__(f"Crop {width}x{height}", parent)
        self._session = session
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._previous_crop: CropRect | None = None

    def redo(self) -> None:
        """Set the crop on the document."""
        self._previous_crop = self._session.document.edit_spec.crop
        new_spec = self._session.document.edit_spec.with_crop(
            self._x, self._y, self._width, self._height
        )
        self._session._set_document(
            Document(edit_spec=new_spec, markers=self._session.document.markers)
        )

    def undo(self) -> None:
        """Restore the previous crop."""
        new_spec = EditSpec(cuts=self._session.document.edit_spec.cuts, crop=self._previous_crop)
        self._session._set_document(
            Document(edit_spec=new_spec, markers=self._session.document.markers)
        )


class AddMarkerCommand(QUndoCommand):
    """Add a marker to the document."""

    def __init__(self, session: EditorSession, marker: Marker, parent: QUndoCommand | None = None):
        super().__init__(f"Add marker at {marker.time:.1f}s", parent)
        self._session = session
        self._marker = marker

    def redo(self) -> None:
        """Add the marker to the document."""
        doc = self._session.document
        new_markers = tuple(sorted(doc.markers + (self._marker,), key=lambda m: m.time))
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=new_markers))

    def undo(self) -> None:
        """Remove the marker from the document."""
        doc = self._session.document
        new_markers = tuple(m for m in doc.markers if m.id != self._marker.id)
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=new_markers))


class RemoveMarkerCommand(QUndoCommand):
    """Remove a marker from the document."""

    def __init__(self, session: EditorSession, marker: Marker, parent: QUndoCommand | None = None):
        super().__init__(f"Remove marker at {marker.time:.1f}s", parent)
        self._session = session
        self._marker = marker

    def redo(self) -> None:
        """Remove the marker from the document."""
        doc = self._session.document
        new_markers = tuple(m for m in doc.markers if m.id != self._marker.id)
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=new_markers))

    def undo(self) -> None:
        """Restore the marker to the document."""
        doc = self._session.document
        new_markers = tuple(sorted(doc.markers + (self._marker,), key=lambda m: m.time))
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=new_markers))


class MoveMarkerCommand(QUndoCommand):
    """Move a marker to a new time."""

    def __init__(
        self,
        session: EditorSession,
        marker_id: str,
        old_time: float,
        new_time: float,
        parent: QUndoCommand | None = None,
    ):
        super().__init__(f"Move marker {old_time:.1f}s → {new_time:.1f}s", parent)
        self._session = session
        self._marker_id = marker_id
        self._old_time = old_time
        self._new_time = new_time

    def redo(self) -> None:
        """Move the marker to the new time."""
        doc = self._session.document
        updated = (
            Marker(id=m.id, time=self._new_time) if m.id == self._marker_id else m
            for m in doc.markers
        )
        new_markers = tuple(sorted(updated, key=lambda m: m.time))
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=new_markers))

    def undo(self) -> None:
        """Move the marker back to the old time."""
        doc = self._session.document
        updated = (
            Marker(id=m.id, time=self._old_time) if m.id == self._marker_id else m
            for m in doc.markers
        )
        new_markers = tuple(sorted(updated, key=lambda m: m.time))
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=new_markers))


class ClearMarkersCommand(QUndoCommand):
    """Clear all markers from the document."""

    def __init__(
        self,
        session: EditorSession,
        markers: tuple[Marker, ...],
        parent: QUndoCommand | None = None,
    ):
        super().__init__("Clear markers", parent)
        self._session = session
        self._markers = markers

    def redo(self) -> None:
        """Remove all markers."""
        doc = self._session.document
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=()))

    def undo(self) -> None:
        """Restore all markers."""
        doc = self._session.document
        self._session._set_document(Document(edit_spec=doc.edit_spec, markers=self._markers))
