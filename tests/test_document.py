"""Tests for Document model - non-destructive editing state."""

import pytest

from video_scissors.document import (
    CropRect,
    CutRegion,
    Document,
    EditSpec,
    Marker,
    effective_duration,
    effective_to_source,
    source_to_effective,
)


class TestCutRegion:
    """Tests for CutRegion dataclass."""

    def test_cut_region_stores_start_and_end(self):
        """CutRegion stores start and end times in source coordinates."""
        cut = CutRegion(start=3.0, end=5.0)

        assert cut.start == 3.0
        assert cut.end == 5.0


class TestCropRect:
    """Tests for CropRect dataclass."""

    def test_crop_rect_stores_dimensions(self):
        """CropRect stores x, y, width, height in source coordinates."""
        crop = CropRect(x=10, y=20, width=100, height=80)

        assert crop.x == 10
        assert crop.y == 20
        assert crop.width == 100
        assert crop.height == 80


class TestEditSpecCreation:
    """Tests for EditSpec creation and basic properties."""

    def test_edit_spec_can_be_created_empty(self):
        """An empty EditSpec has no cuts and no crop."""
        spec = EditSpec()

        assert spec.cuts == ()
        assert spec.crop is None


class TestEditSpecCuts:
    """Tests for adding cuts to EditSpec."""

    def test_with_cut_adds_cut_region(self):
        """with_cut returns a new EditSpec with the cut added."""
        spec = EditSpec()

        new_spec = spec.with_cut(3.0, 5.0)

        assert len(new_spec.cuts) == 1
        assert new_spec.cuts[0].start == 3.0
        assert new_spec.cuts[0].end == 5.0

    def test_with_cut_is_immutable(self):
        """with_cut doesn't modify the original EditSpec."""
        spec = EditSpec()

        spec.with_cut(3.0, 5.0)

        assert spec.cuts == ()

    def test_multiple_cuts_accumulate(self):
        """Multiple cuts can be added."""
        spec = EditSpec()

        spec = spec.with_cut(1.0, 2.0)
        spec = spec.with_cut(5.0, 6.0)

        assert len(spec.cuts) == 2


class TestEffectiveDuration:
    """Tests for effective duration calculation."""

    def test_effective_duration_no_cuts(self):
        """Without cuts, effective duration equals source duration."""
        spec = EditSpec()

        assert effective_duration(10.0, spec) == 10.0

    def test_effective_duration_single_cut(self):
        """Single cut reduces duration by cut length."""
        spec = EditSpec().with_cut(3.0, 5.0)  # 2 seconds removed

        assert effective_duration(10.0, spec) == 8.0

    def test_effective_duration_multiple_cuts(self):
        """Multiple cuts reduce duration by total cut length."""
        spec = EditSpec().with_cut(1.0, 2.0).with_cut(5.0, 7.0)  # 1s + 2s = 3s

        assert effective_duration(10.0, spec) == 7.0


class TestSourceToEffective:
    """Tests for source_to_effective time conversion."""

    def test_source_to_effective_no_cuts(self):
        """Without cuts, source time equals effective time."""
        spec = EditSpec()

        assert source_to_effective(5.0, spec) == 5.0

    def test_source_to_effective_before_cut(self):
        """Time before cut is unchanged."""
        spec = EditSpec().with_cut(5.0, 7.0)

        assert source_to_effective(3.0, spec) == 3.0

    def test_source_to_effective_after_cut(self):
        """Time after cut is shifted earlier by cut duration."""
        spec = EditSpec().with_cut(3.0, 5.0)  # 2 seconds removed

        # Source 7.0 -> Effective 5.0 (shifted by 2s)
        assert source_to_effective(7.0, spec) == 5.0

    def test_source_to_effective_inside_cut(self):
        """Time inside cut clamps to cut start in effective time."""
        spec = EditSpec().with_cut(3.0, 5.0)

        # Any time inside [3, 5) maps to effective 3.0
        assert source_to_effective(4.0, spec) == 3.0

    def test_source_to_effective_multiple_cuts(self):
        """Multiple cuts accumulate their shifts."""
        # 10s video with cuts at [2-3] and [6-8]
        # Source: 0 1 [2-3 CUT] 4 5 [6-8 CUT] 9
        # Effective: 0 1 2 3 [gap] 4 5
        spec = EditSpec().with_cut(2.0, 3.0).with_cut(6.0, 8.0)

        assert source_to_effective(1.0, spec) == 1.0  # Before all cuts
        assert source_to_effective(4.0, spec) == 3.0  # After first cut, -1s
        assert source_to_effective(5.0, spec) == 4.0  # After first cut, -1s
        assert source_to_effective(9.0, spec) == 6.0  # After both cuts, -3s


class TestEffectiveToSource:
    """Tests for effective_to_source time conversion."""

    def test_effective_to_source_no_cuts(self):
        """Without cuts, effective time equals source time."""
        spec = EditSpec()

        assert effective_to_source(5.0, spec) == 5.0

    def test_effective_to_source_before_cut(self):
        """Effective time before cut position is unchanged."""
        spec = EditSpec().with_cut(5.0, 7.0)

        assert effective_to_source(3.0, spec) == 3.0

    def test_effective_to_source_after_cut(self):
        """Effective time after cut is shifted later by cut duration."""
        spec = EditSpec().with_cut(3.0, 5.0)  # 2 seconds removed

        # Effective 4.0 -> Source 6.0 (shifted by 2s)
        assert effective_to_source(4.0, spec) == 6.0

    def test_effective_to_source_multiple_cuts(self):
        """Multiple cuts accumulate their shifts."""
        # Same as above: cuts at [2-3] and [6-8]
        spec = EditSpec().with_cut(2.0, 3.0).with_cut(6.0, 8.0)

        assert effective_to_source(1.0, spec) == 1.0  # Before all cuts
        assert effective_to_source(3.0, spec) == 4.0  # After first cut, +1s
        assert effective_to_source(4.0, spec) == 5.0  # After first cut, +1s
        assert effective_to_source(6.0, spec) == 9.0  # After both cuts, +3s


class TestOverlappingCuts:
    """Tests for merging overlapping cut regions."""

    def test_overlapping_cuts_are_merged(self):
        """Overlapping cuts are merged into a single region."""
        spec = EditSpec().with_cut(2.0, 5.0).with_cut(4.0, 7.0)

        assert len(spec.cuts) == 1
        assert spec.cuts[0].start == 2.0
        assert spec.cuts[0].end == 7.0

    def test_adjacent_cuts_are_merged(self):
        """Adjacent cuts (touching) are merged."""
        spec = EditSpec().with_cut(2.0, 4.0).with_cut(4.0, 6.0)

        assert len(spec.cuts) == 1
        assert spec.cuts[0].start == 2.0
        assert spec.cuts[0].end == 6.0

    def test_contained_cut_is_absorbed(self):
        """A cut fully inside another is absorbed."""
        spec = EditSpec().with_cut(2.0, 8.0).with_cut(4.0, 6.0)

        assert len(spec.cuts) == 1
        assert spec.cuts[0].start == 2.0
        assert spec.cuts[0].end == 8.0

    def test_non_overlapping_cuts_stay_separate(self):
        """Non-overlapping cuts remain separate."""
        spec = EditSpec().with_cut(1.0, 2.0).with_cut(5.0, 6.0)

        assert len(spec.cuts) == 2

    def test_cuts_are_sorted_after_merge(self):
        """Cuts are sorted by start time after merging."""
        spec = EditSpec().with_cut(5.0, 6.0).with_cut(1.0, 2.0)

        assert spec.cuts[0].start == 1.0
        assert spec.cuts[1].start == 5.0


class TestEditSpecCrop:
    """Tests for crop operations."""

    def test_with_crop_sets_crop(self):
        """with_crop returns a new EditSpec with crop set."""
        spec = EditSpec()

        new_spec = spec.with_crop(10, 20, 100, 80)

        assert new_spec.crop is not None
        assert new_spec.crop.x == 10
        assert new_spec.crop.y == 20
        assert new_spec.crop.width == 100
        assert new_spec.crop.height == 80

    def test_with_crop_is_immutable(self):
        """with_crop doesn't modify the original EditSpec."""
        spec = EditSpec()

        spec.with_crop(10, 20, 100, 80)

        assert spec.crop is None

    def test_with_crop_replaces_existing_crop(self):
        """New crop replaces existing crop."""
        spec = EditSpec().with_crop(10, 20, 100, 80)

        new_spec = spec.with_crop(50, 60, 200, 150)

        assert new_spec.crop.x == 50
        assert new_spec.crop.width == 200

    def test_with_crop_preserves_cuts(self):
        """Adding a crop preserves existing cuts."""
        spec = EditSpec().with_cut(1.0, 2.0)

        new_spec = spec.with_crop(10, 20, 100, 80)

        assert len(new_spec.cuts) == 1
        assert new_spec.crop is not None


class TestTimeConversionEdgeCases:
    """Tests for edge cases in time conversion."""

    def test_source_to_effective_at_cut_start(self):
        """Time exactly at cut start maps to that effective time."""
        spec = EditSpec().with_cut(3.0, 5.0)

        # At cut start: should be effective 3.0 (no shift yet)
        assert source_to_effective(3.0, spec) == 3.0

    def test_source_to_effective_at_cut_end(self):
        """Time exactly at cut end is shifted by full cut duration."""
        spec = EditSpec().with_cut(3.0, 5.0)

        # At cut end (5.0): shifted by 2s -> effective 3.0
        assert source_to_effective(5.0, spec) == 3.0

    def test_effective_to_source_at_cut_boundary(self):
        """Effective time at cut boundary maps correctly."""
        spec = EditSpec().with_cut(3.0, 5.0)

        # Effective 3.0 is exactly where cut was, maps to source 5.0
        assert effective_to_source(3.0, spec) == 5.0


class TestTimeConversionRoundtrip:
    """Tests for roundtrip conversion consistency."""

    def test_roundtrip_no_cuts(self):
        """Roundtrip works with no cuts."""
        spec = EditSpec()

        for t in [0.0, 2.5, 5.0, 10.0]:
            assert effective_to_source(source_to_effective(t, spec), spec) == t

    def test_roundtrip_single_cut(self):
        """Roundtrip works with single cut (for times outside cut)."""
        spec = EditSpec().with_cut(3.0, 5.0)

        # Times outside the cut should roundtrip
        for t in [0.0, 1.0, 2.0, 5.0, 7.0, 10.0]:
            eff = source_to_effective(t, spec)
            back = effective_to_source(eff, spec)
            assert back == t, f"Roundtrip failed for {t}: {t} -> {eff} -> {back}"

    def test_roundtrip_multiple_cuts(self):
        """Roundtrip works with multiple cuts (for times outside cuts)."""
        spec = EditSpec().with_cut(2.0, 3.0).with_cut(6.0, 8.0)

        # Times outside cuts should roundtrip
        for t in [0.0, 1.0, 4.0, 5.0, 9.0, 10.0]:
            eff = source_to_effective(t, spec)
            back = effective_to_source(eff, spec)
            assert back == t, f"Roundtrip failed for {t}"


class TestMarker:
    """Tests for Marker dataclass."""

    def test_marker_stores_id_and_time(self):
        """Marker stores id and time."""
        marker = Marker(id="abc123", time=5.5)

        assert marker.id == "abc123"
        assert marker.time == 5.5

    def test_marker_create_generates_id(self):
        """Marker.create generates a unique id."""
        marker1 = Marker.create(3.0)
        marker2 = Marker.create(3.0)

        assert marker1.id != marker2.id
        assert marker1.time == 3.0
        assert marker2.time == 3.0


class TestDocument:
    """Tests for Document dataclass."""

    def test_document_can_be_created_empty(self):
        """An empty Document has default edit_spec and no markers."""
        doc = Document()

        assert doc.edit_spec == EditSpec()
        assert doc.markers == ()

    def test_document_stores_edit_spec(self):
        """Document stores the provided edit_spec."""
        spec = EditSpec().with_cut(1.0, 2.0)
        doc = Document(edit_spec=spec)

        assert doc.edit_spec == spec
        assert len(doc.edit_spec.cuts) == 1

    def test_document_stores_markers(self):
        """Document stores the provided markers."""
        markers = (Marker.create(1.0), Marker.create(3.0))
        doc = Document(markers=markers)

        assert len(doc.markers) == 2
        assert doc.markers[0].time == 1.0
        assert doc.markers[1].time == 3.0

    def test_document_is_immutable(self):
        """Document is a frozen dataclass."""
        doc = Document()

        # Frozen dataclass raises on attribute assignment
        with pytest.raises((AttributeError, TypeError)):
            doc.edit_spec = EditSpec().with_cut(1.0, 2.0)  # type: ignore
