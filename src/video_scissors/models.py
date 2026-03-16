"""QObject models for exposing domain state to QML.

These models wrap the frozen domain dataclasses (EditSpec, Document)
as QObjects with per-property notify signals. They don't own data —
the session updates them when domain state changes, and they emit
fine-grained signals so QML bindings react to exactly what changed.
"""

from PySide6.QtCore import Property, QObject, Signal

from video_scissors.document import Document, EditSpec


class EditSpecModel(QObject):
    """QML-facing model for the EditSpec.

    Wraps the frozen EditSpec dataclass, exposing each piece of state
    as a Qt Property with its own notify signal.
    """

    cutsChanged = Signal()
    cropChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._spec = EditSpec()

    @Property(list, notify=cutsChanged)
    def cutRegions(self) -> list[dict]:
        """Cut regions as list of {start, end} in milliseconds for QML."""
        return [{"start": int(c.start * 1000), "end": int(c.end * 1000)} for c in self._spec.cuts]

    @Property(bool, notify=cutsChanged)
    def hasCuts(self) -> bool:
        """True if there are cut regions."""
        return len(self._spec.cuts) > 0

    @Property("QVariant", notify=cropChanged)
    def cropRect(self) -> dict | None:
        """Crop rectangle as {x, y, width, height} or None."""
        crop = self._spec.crop
        if crop is None:
            return None
        return {"x": crop.x, "y": crop.y, "width": crop.width, "height": crop.height}

    @Property(bool, notify=cropChanged)
    def hasCrop(self) -> bool:
        """True if a crop is set."""
        return self._spec.crop is not None

    def _update(self, new_spec: EditSpec) -> None:
        """Update the underlying spec and emit signals for changed properties."""
        old = self._spec
        self._spec = new_spec
        if old.cuts != new_spec.cuts:
            self.cutsChanged.emit()
        if old.crop != new_spec.crop:
            self.cropChanged.emit()


class DocumentModel(QObject):
    """QML-facing model for the Document.

    Wraps the frozen Document dataclass, exposing the edit spec
    (as an EditSpecModel sub-object) and markers.
    """

    markersChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._doc = Document()
        self._edit_spec_model = EditSpecModel(self)

    @Property(QObject, constant=True)
    def editSpec(self) -> EditSpecModel:
        """The edit spec sub-model (stable QObject identity)."""
        return self._edit_spec_model

    @Property(list, notify=markersChanged)
    def markers(self) -> list[dict]:
        """Cut markers as list of {id, time} objects for QML."""
        return [{"id": m.id, "time": m.time} for m in self._doc.markers]

    def _update(self, new_doc: Document) -> None:
        """Update the underlying document and emit signals for changed properties."""
        old = self._doc
        self._doc = new_doc
        if old.edit_spec != new_doc.edit_spec:
            self._edit_spec_model._update(new_doc.edit_spec)
        if old.markers != new_doc.markers:
            self.markersChanged.emit()
