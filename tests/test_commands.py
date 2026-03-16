"""Tests for command-based undo architecture."""

from pathlib import Path

from video_scissors.commands import (
    AddCutCommand,
    AddMarkerCommand,
    ClearMarkersCommand,
    MoveMarkerCommand,
    RemoveMarkerCommand,
    SetCropCommand,
)
from video_scissors.document import CropRect, Document, EditSpec, Marker
from video_scissors.session import EditorSession


class TestAddCutCommand:
    """Tests for AddCutCommand."""

    def test_execute_adds_cut_to_document(self):
        """Execute adds a cut region to the document's edit_spec."""
        doc = Document()
        cmd = AddCutCommand(start=1.0, end=2.0)

        result = cmd.execute(doc)

        assert len(result.edit_spec.cuts) == 1
        assert result.edit_spec.cuts[0].start == 1.0
        assert result.edit_spec.cuts[0].end == 2.0

    def test_execute_preserves_markers(self):
        """Execute preserves existing markers."""
        marker = Marker.create(0.5)
        doc = Document(markers=(marker,))
        cmd = AddCutCommand(start=1.0, end=2.0)

        result = cmd.execute(doc)

        assert result.markers == (marker,)

    def test_undo_removes_the_cut(self):
        """Undo removes the cut that was added."""
        doc = Document()
        cmd = AddCutCommand(start=1.0, end=2.0)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.edit_spec.cuts == ()

    def test_undo_preserves_other_cuts(self):
        """Undo only removes the specific cut added by this command."""
        # Pre-existing cut
        existing_spec = EditSpec().with_cut(3.0, 4.0)
        doc = Document(edit_spec=existing_spec)
        cmd = AddCutCommand(start=1.0, end=2.0)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        # Only the pre-existing cut remains
        assert len(result.edit_spec.cuts) == 1
        assert result.edit_spec.cuts[0].start == 3.0


class TestSetCropCommand:
    """Tests for SetCropCommand."""

    def test_execute_sets_crop(self):
        """Execute sets the crop on the document."""
        doc = Document()
        cmd = SetCropCommand(x=10, y=20, width=100, height=80)

        result = cmd.execute(doc)

        assert result.edit_spec.crop == CropRect(10, 20, 100, 80)

    def test_execute_replaces_existing_crop(self):
        """Execute replaces any existing crop."""
        existing_spec = EditSpec(crop=CropRect(0, 0, 50, 50))
        doc = Document(edit_spec=existing_spec)
        cmd = SetCropCommand(x=10, y=20, width=100, height=80)

        result = cmd.execute(doc)

        assert result.edit_spec.crop == CropRect(10, 20, 100, 80)

    def test_undo_restores_previous_crop(self):
        """Undo restores the previous crop (or None)."""
        existing_crop = CropRect(0, 0, 50, 50)
        existing_spec = EditSpec(crop=existing_crop)
        doc = Document(edit_spec=existing_spec)
        cmd = SetCropCommand(x=10, y=20, width=100, height=80, previous_crop=existing_crop)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.edit_spec.crop == existing_crop

    def test_undo_removes_crop_when_no_previous(self):
        """Undo removes crop when there was no previous crop."""
        doc = Document()
        cmd = SetCropCommand(x=10, y=20, width=100, height=80, previous_crop=None)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.edit_spec.crop is None


class TestAddMarkerCommand:
    """Tests for AddMarkerCommand."""

    def test_execute_adds_marker(self):
        """Execute adds a marker to the document."""
        doc = Document()
        marker = Marker.create(1.5)
        cmd = AddMarkerCommand(marker=marker)

        result = cmd.execute(doc)

        assert len(result.markers) == 1
        assert result.markers[0] == marker

    def test_execute_keeps_markers_sorted(self):
        """Execute maintains markers in sorted order."""
        existing_marker = Marker.create(2.0)
        doc = Document(markers=(existing_marker,))
        new_marker = Marker.create(1.0)
        cmd = AddMarkerCommand(marker=new_marker)

        result = cmd.execute(doc)

        assert result.markers[0].time == 1.0
        assert result.markers[1].time == 2.0

    def test_undo_removes_marker(self):
        """Undo removes the marker that was added."""
        doc = Document()
        marker = Marker.create(1.5)
        cmd = AddMarkerCommand(marker=marker)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers == ()

    def test_undo_preserves_other_markers(self):
        """Undo only removes the specific marker added."""
        existing_marker = Marker.create(2.0)
        doc = Document(markers=(existing_marker,))
        new_marker = Marker.create(1.0)
        cmd = AddMarkerCommand(marker=new_marker)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers == (existing_marker,)


class TestRemoveMarkerCommand:
    """Tests for RemoveMarkerCommand."""

    def test_execute_removes_marker(self):
        """Execute removes the specified marker."""
        marker = Marker.create(1.5)
        doc = Document(markers=(marker,))
        cmd = RemoveMarkerCommand(marker=marker)

        result = cmd.execute(doc)

        assert result.markers == ()

    def test_execute_preserves_other_markers(self):
        """Execute only removes the specific marker."""
        marker1 = Marker.create(1.0)
        marker2 = Marker.create(2.0)
        doc = Document(markers=(marker1, marker2))
        cmd = RemoveMarkerCommand(marker=marker1)

        result = cmd.execute(doc)

        assert result.markers == (marker2,)

    def test_undo_restores_marker(self):
        """Undo restores the removed marker."""
        marker = Marker.create(1.5)
        doc = Document(markers=(marker,))
        cmd = RemoveMarkerCommand(marker=marker)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers == (marker,)

    def test_undo_maintains_sort_order(self):
        """Undo maintains markers in sorted order."""
        marker1 = Marker.create(1.0)
        marker2 = Marker.create(3.0)
        doc = Document(markers=(marker1, marker2))
        # Remove marker1, leaving marker2
        cmd = RemoveMarkerCommand(marker=marker1)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers[0].time == 1.0
        assert result.markers[1].time == 3.0


class TestClearMarkersCommand:
    """Tests for ClearMarkersCommand."""

    def test_execute_removes_all_markers(self):
        """Execute removes all markers from the document."""
        marker1 = Marker.create(1.0)
        marker2 = Marker.create(2.0)
        doc = Document(markers=(marker1, marker2))
        cmd = ClearMarkersCommand(markers=(marker1, marker2))

        result = cmd.execute(doc)

        assert result.markers == ()

    def test_undo_restores_all_markers(self):
        """Undo restores all cleared markers."""
        marker1 = Marker.create(1.0)
        marker2 = Marker.create(2.0)
        doc = Document(markers=(marker1, marker2))
        cmd = ClearMarkersCommand(markers=(marker1, marker2))
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers == (marker1, marker2)


class TestMoveMarkerCommand:
    """Tests for MoveMarkerCommand."""

    def test_execute_moves_marker(self):
        """Execute moves the marker to a new time."""
        marker = Marker(id="test-id", time=1.0)
        doc = Document(markers=(marker,))
        cmd = MoveMarkerCommand(marker_id="test-id", old_time=1.0, new_time=2.0)

        result = cmd.execute(doc)

        assert len(result.markers) == 1
        assert result.markers[0].id == "test-id"
        assert result.markers[0].time == 2.0

    def test_execute_maintains_sort_order(self):
        """Execute maintains markers in sorted order after move."""
        marker1 = Marker(id="m1", time=1.0)
        marker2 = Marker(id="m2", time=2.0)
        marker3 = Marker(id="m3", time=3.0)
        doc = Document(markers=(marker1, marker2, marker3))
        # Move marker1 to between marker2 and marker3
        cmd = MoveMarkerCommand(marker_id="m1", old_time=1.0, new_time=2.5)

        result = cmd.execute(doc)

        times = [m.time for m in result.markers]
        assert times == [2.0, 2.5, 3.0]

    def test_undo_restores_original_time(self):
        """Undo moves the marker back to its original time."""
        marker = Marker(id="test-id", time=1.0)
        doc = Document(markers=(marker,))
        cmd = MoveMarkerCommand(marker_id="test-id", old_time=1.0, new_time=2.0)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers[0].time == 1.0

    def test_undo_maintains_sort_order(self):
        """Undo maintains markers in sorted order."""
        marker1 = Marker(id="m1", time=1.0)
        marker2 = Marker(id="m2", time=2.0)
        doc = Document(markers=(marker1, marker2))
        # Move marker2 before marker1
        cmd = MoveMarkerCommand(marker_id="m2", old_time=2.0, new_time=0.5)
        after_execute = cmd.execute(doc)

        result = cmd.undo(after_execute)

        assert result.markers[0].time == 1.0
        assert result.markers[1].time == 2.0


class TestSessionExecuteCommand:
    """Tests for session.execute() with commands."""

    def test_execute_applies_command_to_document(self, test_video: Path):
        """execute() applies the command to the document."""
        session = EditorSession()
        session.load(test_video)
        cmd = AddCutCommand(start=1.0, end=2.0)

        session.execute(cmd)

        assert len(session.document.edit_spec.cuts) == 1
        assert session.document.edit_spec.cuts[0].start == 1.0

    def test_execute_enables_undo(self, test_video: Path):
        """execute() enables undo."""
        session = EditorSession()
        session.load(test_video)
        cmd = AddCutCommand(start=1.0, end=2.0)

        session.execute(cmd)

        assert session.can_undo is True

    def test_execute_clears_redo_stack(self, test_video: Path):
        """execute() clears the redo stack."""
        session = EditorSession()
        session.load(test_video)
        session.execute(AddCutCommand(start=1.0, end=2.0))
        session.undo()
        assert session.can_redo is True

        session.execute(AddCutCommand(start=3.0, end=4.0))

        assert session.can_redo is False

    def test_undo_reverses_command(self, test_video: Path):
        """undo() reverses the last command."""
        session = EditorSession()
        session.load(test_video)
        session.execute(AddCutCommand(start=1.0, end=2.0))

        session.undo()

        assert session.document.edit_spec.cuts == ()

    def test_redo_reapplies_command(self, test_video: Path):
        """redo() reapplies the undone command."""
        session = EditorSession()
        session.load(test_video)
        session.execute(AddCutCommand(start=1.0, end=2.0))
        session.undo()

        session.redo()

        assert len(session.document.edit_spec.cuts) == 1

    def test_multiple_commands_undo_in_order(self, test_video: Path):
        """Multiple commands can be undone in reverse order."""
        session = EditorSession()
        session.load(test_video)
        session.execute(AddCutCommand(start=1.0, end=2.0))
        session.execute(AddCutCommand(start=3.0, end=4.0))

        session.undo()
        assert len(session.document.edit_spec.cuts) == 1
        assert session.document.edit_spec.cuts[0].start == 1.0

        session.undo()
        assert session.document.edit_spec.cuts == ()

    def test_execute_works_with_set_crop_command(self, test_video: Path):
        """execute() works with SetCropCommand."""
        session = EditorSession()
        session.load(test_video)
        prev_crop = session.document.edit_spec.crop
        cmd = SetCropCommand(x=10, y=20, width=100, height=80, previous_crop=prev_crop)

        session.execute(cmd)

        assert session.document.edit_spec.crop == CropRect(10, 20, 100, 80)

    def test_execute_works_with_marker_commands(self, test_video: Path):
        """execute() works with marker commands."""
        session = EditorSession()
        session.load(test_video)
        marker = Marker.create(1.5)
        cmd = AddMarkerCommand(marker=marker)

        session.execute(cmd)

        assert session.markers == (marker,)

    def test_last_command_property(self, test_video: Path):
        """last_command returns the most recent command (for signal emission)."""
        session = EditorSession()
        session.load(test_video)
        cmd = AddCutCommand(start=1.0, end=2.0)

        session.execute(cmd)

        assert session.last_command is cmd

    def test_last_command_none_after_undo(self, test_video: Path):
        """last_command is None after undo (undo is not a command)."""
        session = EditorSession()
        session.load(test_video)
        session.execute(AddCutCommand(start=1.0, end=2.0))

        session.undo()

        assert session.last_command is None
