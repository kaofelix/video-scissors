"""Command-based undo architecture.

Commands are first-class objects that know how to execute and undo.
Each command transforms a Document and can reverse that transformation.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from video_scissors.document import CropRect, Document, EditSpec, Marker

if TYPE_CHECKING:
    from video_scissors.session import SessionSnapshot


class Command(Protocol):
    """Protocol for undoable commands."""

    def execute(self, doc: Document) -> Document:
        """Apply the command to the document."""
        ...

    def undo(self, doc: Document) -> Document:
        """Reverse the command on the document."""
        ...


@dataclass(frozen=True)
class SnapshotCommand:
    """Legacy command that restores a full snapshot.

    Used for operations that change working video (destructive edits).
    This exists for backward compatibility and should eventually be removed.
    """

    previous_snapshot: "SessionSnapshot"
    new_snapshot: "SessionSnapshot"

    def execute(self, doc: Document) -> Document:
        """Return the new snapshot's document."""
        return self.new_snapshot.document

    def undo(self, doc: Document) -> Document:
        """Return the previous snapshot's document."""
        return self.previous_snapshot.document


@dataclass(frozen=True)
class AddCutCommand:
    """Add a cut region to the edit spec."""

    start: float  # source time in seconds
    end: float  # source time in seconds

    def execute(self, doc: Document) -> Document:
        """Add the cut to the document."""
        new_spec = doc.edit_spec.with_cut(self.start, self.end)
        return Document(edit_spec=new_spec, markers=doc.markers)

    def undo(self, doc: Document) -> Document:
        """Remove the cut from the document."""
        # Find and remove the cut we added
        remaining = tuple(
            c for c in doc.edit_spec.cuts if not (c.start == self.start and c.end == self.end)
        )
        new_spec = EditSpec(cuts=remaining, crop=doc.edit_spec.crop)
        return Document(edit_spec=new_spec, markers=doc.markers)


@dataclass(frozen=True)
class SetCropCommand:
    """Set crop region on the edit spec."""

    x: int
    y: int
    width: int
    height: int
    previous_crop: CropRect | None = None

    def execute(self, doc: Document) -> Document:
        """Set the crop on the document."""
        new_spec = doc.edit_spec.with_crop(self.x, self.y, self.width, self.height)
        return Document(edit_spec=new_spec, markers=doc.markers)

    def undo(self, doc: Document) -> Document:
        """Restore the previous crop."""
        new_spec = EditSpec(cuts=doc.edit_spec.cuts, crop=self.previous_crop)
        return Document(edit_spec=new_spec, markers=doc.markers)


@dataclass(frozen=True)
class AddMarkerCommand:
    """Add a marker to the document."""

    marker: Marker

    def execute(self, doc: Document) -> Document:
        """Add the marker to the document."""
        new_markers = tuple(sorted(doc.markers + (self.marker,), key=lambda m: m.time))
        return Document(edit_spec=doc.edit_spec, markers=new_markers)

    def undo(self, doc: Document) -> Document:
        """Remove the marker from the document."""
        new_markers = tuple(m for m in doc.markers if m.id != self.marker.id)
        return Document(edit_spec=doc.edit_spec, markers=new_markers)


@dataclass(frozen=True)
class RemoveMarkerCommand:
    """Remove a marker from the document."""

    marker: Marker

    def execute(self, doc: Document) -> Document:
        """Remove the marker from the document."""
        new_markers = tuple(m for m in doc.markers if m.id != self.marker.id)
        return Document(edit_spec=doc.edit_spec, markers=new_markers)

    def undo(self, doc: Document) -> Document:
        """Restore the marker to the document."""
        new_markers = tuple(sorted(doc.markers + (self.marker,), key=lambda m: m.time))
        return Document(edit_spec=doc.edit_spec, markers=new_markers)


@dataclass(frozen=True)
class MoveMarkerCommand:
    """Move a marker to a new time."""

    marker_id: str
    old_time: float
    new_time: float

    def execute(self, doc: Document) -> Document:
        """Move the marker to the new time."""
        updated = (
            Marker(id=m.id, time=self.new_time) if m.id == self.marker_id else m
            for m in doc.markers
        )
        new_markers = tuple(sorted(updated, key=lambda m: m.time))
        return Document(edit_spec=doc.edit_spec, markers=new_markers)

    def undo(self, doc: Document) -> Document:
        """Move the marker back to the old time."""
        updated = (
            Marker(id=m.id, time=self.old_time) if m.id == self.marker_id else m
            for m in doc.markers
        )
        new_markers = tuple(sorted(updated, key=lambda m: m.time))
        return Document(edit_spec=doc.edit_spec, markers=new_markers)


@dataclass(frozen=True)
class ClearMarkersCommand:
    """Clear all markers from the document."""

    markers: tuple[Marker, ...]  # Store for undo

    def execute(self, doc: Document) -> Document:
        """Remove all markers."""
        return Document(edit_spec=doc.edit_spec, markers=())

    def undo(self, doc: Document) -> Document:
        """Restore all markers."""
        return Document(edit_spec=doc.edit_spec, markers=self.markers)
