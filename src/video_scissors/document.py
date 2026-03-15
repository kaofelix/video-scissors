"""Document model - non-destructive editing state."""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CutRegion:
    """A segment to be removed. Always in SOURCE time."""

    start: float  # seconds, source time
    end: float  # seconds, source time


@dataclass(frozen=True)
class CropRect:
    """Crop parameters in source video coordinates."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class EditSpec:
    """Render recipe - transforms source into output.

    Contains the edits that affect the final rendered output.
    All coordinates are in source time/space.
    """

    cuts: tuple[CutRegion, ...] = field(default_factory=tuple)
    crop: CropRect | None = None

    def with_cut(self, start: float, end: float) -> "EditSpec":
        """Add a cut. Times must be in SOURCE time."""
        new_cut = CutRegion(start, end)
        merged = _merge_overlapping_cuts(self.cuts + (new_cut,))
        return EditSpec(cuts=merged, crop=self.crop)

    def with_crop(self, x: int, y: int, width: int, height: int) -> "EditSpec":
        """Set crop parameters. Replaces any existing crop."""
        new_crop = CropRect(x, y, width, height)
        return EditSpec(cuts=self.cuts, crop=new_crop)


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
class Document:
    """Complete editing state.

    Contains everything needed to describe the current edit:
    - edit_spec: What affects the output (render recipe)
    - markers: Editing helpers (don't affect output)
    """

    edit_spec: EditSpec = field(default_factory=EditSpec)
    markers: tuple[Marker, ...] = field(default_factory=tuple)


# --- Pure functions for coordinate conversion ---


def _merge_overlapping_cuts(cuts: tuple[CutRegion, ...]) -> tuple[CutRegion, ...]:
    """Merge overlapping or adjacent cut regions."""
    if not cuts:
        return ()
    sorted_cuts = sorted(cuts, key=lambda c: c.start)
    merged: list[CutRegion] = [sorted_cuts[0]]
    for cut in sorted_cuts[1:]:
        if cut.start <= merged[-1].end:
            # Overlapping or adjacent: extend the last cut
            merged[-1] = CutRegion(merged[-1].start, max(merged[-1].end, cut.end))
        else:
            merged.append(cut)
    return tuple(merged)


def source_to_effective(source_time: float, edit_spec: EditSpec) -> float:
    """Convert source time to effective (display) time.

    Example: source=5s with cut at 3-4s → effective=4s
    """
    effective = source_time
    for cut in sorted(edit_spec.cuts, key=lambda c: c.start):
        if source_time >= cut.end:
            # Past this cut: subtract full cut duration
            effective -= cut.end - cut.start
        elif source_time > cut.start:
            # Inside cut: clamp to cut start
            effective -= source_time - cut.start
    return max(0.0, effective)


def effective_to_source(effective_time: float, edit_spec: EditSpec) -> float:
    """Convert effective (display) time to source time.

    Used when user clicks timeline or sets markers.
    Example: effective=4s with cut at 3-4s → source=5s
    """
    source = effective_time
    for cut in sorted(edit_spec.cuts, key=lambda c: c.start):
        # If we've passed where this cut starts in effective time
        cut_start_effective = source_to_effective(cut.start, edit_spec)
        if effective_time >= cut_start_effective:
            source += cut.end - cut.start
    return source


def effective_duration(source_duration: float, edit_spec: EditSpec) -> float:
    """Total duration after all cuts applied."""
    cut_total = sum(c.end - c.start for c in edit_spec.cuts)
    return source_duration - cut_total
