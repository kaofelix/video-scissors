"""Tests for command-based undo architecture."""

from pathlib import Path

import pytest

from video_scissors.commands import (
    AddCutCommand,
    AddMarkerCommand,
    ClearMarkersCommand,
    MoveMarkerCommand,
    RemoveMarkerCommand,
    SetCropCommand,
)
from video_scissors.document import CropRect, Marker
from video_scissors.session import EditorSession


@pytest.fixture
def session_with_video(test_video: Path) -> EditorSession:
    """Create a session with a loaded video."""
    session = EditorSession()
    session.load(test_video)
    return session


class TestAddCutCommand:
    """Tests for AddCutCommand."""

    def test_redo_adds_cut_to_document(self, session_with_video: EditorSession):
        """Redo adds a cut region to the document's edit_spec."""
        cmd = AddCutCommand(session_with_video, start=1.0, end=2.0)

        cmd.redo()

        assert len(session_with_video.document.edit_spec.cuts) == 1
        assert session_with_video.document.edit_spec.cuts[0].start == 1.0
        assert session_with_video.document.edit_spec.cuts[0].end == 2.0

    def test_redo_preserves_markers(self, session_with_video: EditorSession):
        """Redo preserves existing markers."""
        original_marker = session_with_video.add_marker(0.5)
        session_with_video.undo_stack.clear()  # Clear the add_marker command

        cmd = AddCutCommand(session_with_video, start=1.0, end=2.0)
        cmd.redo()

        assert session_with_video.markers[0].id == original_marker.id

    def test_undo_removes_the_cut(self, session_with_video: EditorSession):
        """Undo removes the cut that was added."""
        cmd = AddCutCommand(session_with_video, start=1.0, end=2.0)
        cmd.redo()

        cmd.undo()

        assert session_with_video.document.edit_spec.cuts == ()

    def test_undo_preserves_other_cuts(self, session_with_video: EditorSession):
        """Undo only removes the specific cut added by this command."""
        # Pre-existing cut via the session
        session_with_video.add_cut(3.0, 4.0)
        session_with_video.undo_stack.clear()

        cmd = AddCutCommand(session_with_video, start=1.0, end=2.0)
        cmd.redo()
        cmd.undo()

        # Only the pre-existing cut remains
        assert len(session_with_video.document.edit_spec.cuts) == 1
        assert session_with_video.document.edit_spec.cuts[0].start == 3.0

    def test_command_text(self, session_with_video: EditorSession):
        """Command has descriptive text."""
        cmd = AddCutCommand(session_with_video, start=1.5, end=2.5)

        assert "1.5" in cmd.text()
        assert "2.5" in cmd.text()


class TestSetCropCommand:
    """Tests for SetCropCommand."""

    def test_redo_sets_crop(self, session_with_video: EditorSession):
        """Redo sets the crop on the document."""
        cmd = SetCropCommand(session_with_video, x=10, y=20, width=100, height=80)

        cmd.redo()

        assert session_with_video.document.edit_spec.crop == CropRect(10, 20, 100, 80)

    def test_redo_replaces_existing_crop(self, session_with_video: EditorSession):
        """Redo replaces any existing crop."""
        session_with_video.set_crop(0, 0, 50, 50)
        session_with_video.undo_stack.clear()

        cmd = SetCropCommand(session_with_video, x=10, y=20, width=100, height=80)
        cmd.redo()

        assert session_with_video.document.edit_spec.crop == CropRect(10, 20, 100, 80)

    def test_undo_restores_previous_crop(self, session_with_video: EditorSession):
        """Undo restores the previous crop."""
        session_with_video.set_crop(0, 0, 50, 50)
        session_with_video.undo_stack.clear()

        cmd = SetCropCommand(session_with_video, x=10, y=20, width=100, height=80)
        cmd.redo()
        cmd.undo()

        assert session_with_video.document.edit_spec.crop == CropRect(0, 0, 50, 50)

    def test_undo_removes_crop_when_no_previous(self, session_with_video: EditorSession):
        """Undo removes crop when there was no previous crop."""
        cmd = SetCropCommand(session_with_video, x=10, y=20, width=100, height=80)
        cmd.redo()

        cmd.undo()

        assert session_with_video.document.edit_spec.crop is None

    def test_command_text(self, session_with_video: EditorSession):
        """Command has descriptive text."""
        cmd = SetCropCommand(session_with_video, x=10, y=20, width=100, height=80)

        assert "100" in cmd.text()
        assert "80" in cmd.text()


class TestAddMarkerCommand:
    """Tests for AddMarkerCommand."""

    def test_redo_adds_marker(self, session_with_video: EditorSession):
        """Redo adds a marker to the document."""
        marker = Marker.create(1.5)
        cmd = AddMarkerCommand(session_with_video, marker=marker)

        cmd.redo()

        assert len(session_with_video.markers) == 1
        assert session_with_video.markers[0] == marker

    def test_redo_keeps_markers_sorted(self, session_with_video: EditorSession):
        """Redo maintains markers in sorted order."""
        session_with_video.add_marker(2.0)
        session_with_video.undo_stack.clear()

        new_marker = Marker.create(1.0)
        cmd = AddMarkerCommand(session_with_video, marker=new_marker)
        cmd.redo()

        assert session_with_video.markers[0].time == 1.0
        assert session_with_video.markers[1].time == 2.0

    def test_undo_removes_marker(self, session_with_video: EditorSession):
        """Undo removes the marker that was added."""
        marker = Marker.create(1.5)
        cmd = AddMarkerCommand(session_with_video, marker=marker)
        cmd.redo()

        cmd.undo()

        assert session_with_video.markers == ()

    def test_undo_preserves_other_markers(self, session_with_video: EditorSession):
        """Undo only removes the specific marker added."""
        other_marker = session_with_video.add_marker(2.0)
        session_with_video.undo_stack.clear()

        new_marker = Marker.create(1.0)
        cmd = AddMarkerCommand(session_with_video, marker=new_marker)
        cmd.redo()
        cmd.undo()

        assert len(session_with_video.markers) == 1
        assert session_with_video.markers[0].id == other_marker.id

    def test_command_text(self, session_with_video: EditorSession):
        """Command has descriptive text."""
        marker = Marker.create(1.5)
        cmd = AddMarkerCommand(session_with_video, marker=marker)

        assert "1.5" in cmd.text()


class TestRemoveMarkerCommand:
    """Tests for RemoveMarkerCommand."""

    def test_redo_removes_marker(self, session_with_video: EditorSession):
        """Redo removes the specified marker."""
        marker = session_with_video.add_marker(1.5)
        session_with_video.undo_stack.clear()

        cmd = RemoveMarkerCommand(session_with_video, marker=marker)
        cmd.redo()

        assert session_with_video.markers == ()

    def test_redo_preserves_other_markers(self, session_with_video: EditorSession):
        """Redo only removes the specific marker."""
        marker1 = session_with_video.add_marker(1.0)
        marker2 = session_with_video.add_marker(2.0)
        session_with_video.undo_stack.clear()

        cmd = RemoveMarkerCommand(session_with_video, marker=marker1)
        cmd.redo()

        assert len(session_with_video.markers) == 1
        assert session_with_video.markers[0].id == marker2.id

    def test_undo_restores_marker(self, session_with_video: EditorSession):
        """Undo restores the removed marker."""
        marker = session_with_video.add_marker(1.5)
        session_with_video.undo_stack.clear()

        cmd = RemoveMarkerCommand(session_with_video, marker=marker)
        cmd.redo()
        cmd.undo()

        assert len(session_with_video.markers) == 1
        assert session_with_video.markers[0].id == marker.id

    def test_undo_maintains_sort_order(self, session_with_video: EditorSession):
        """Undo maintains markers in sorted order."""
        marker1 = session_with_video.add_marker(1.0)
        session_with_video.add_marker(3.0)
        session_with_video.undo_stack.clear()

        cmd = RemoveMarkerCommand(session_with_video, marker=marker1)
        cmd.redo()
        cmd.undo()

        assert session_with_video.markers[0].time == 1.0
        assert session_with_video.markers[1].time == 3.0


class TestClearMarkersCommand:
    """Tests for ClearMarkersCommand."""

    def test_redo_removes_all_markers(self, session_with_video: EditorSession):
        """Redo removes all markers from the document."""
        marker1 = session_with_video.add_marker(1.0)
        marker2 = session_with_video.add_marker(2.0)
        session_with_video.undo_stack.clear()

        cmd = ClearMarkersCommand(session_with_video, markers=(marker1, marker2))
        cmd.redo()

        assert session_with_video.markers == ()

    def test_undo_restores_all_markers(self, session_with_video: EditorSession):
        """Undo restores all cleared markers."""
        marker1 = session_with_video.add_marker(1.0)
        marker2 = session_with_video.add_marker(2.0)
        session_with_video.undo_stack.clear()

        cmd = ClearMarkersCommand(session_with_video, markers=(marker1, marker2))
        cmd.redo()
        cmd.undo()

        assert len(session_with_video.markers) == 2


class TestMoveMarkerCommand:
    """Tests for MoveMarkerCommand."""

    def test_redo_moves_marker(self, session_with_video: EditorSession):
        """Redo moves the marker to a new time."""
        marker = session_with_video.add_marker(1.0)
        session_with_video.undo_stack.clear()

        cmd = MoveMarkerCommand(session_with_video, marker.id, old_time=1.0, new_time=2.0)
        cmd.redo()

        assert len(session_with_video.markers) == 1
        assert session_with_video.markers[0].id == marker.id
        assert session_with_video.markers[0].time == 2.0

    def test_redo_maintains_sort_order(self, session_with_video: EditorSession):
        """Redo maintains markers in sorted order after move."""
        marker1 = session_with_video.add_marker(1.0)
        session_with_video.add_marker(2.0)
        session_with_video.add_marker(3.0)
        session_with_video.undo_stack.clear()

        cmd = MoveMarkerCommand(session_with_video, marker1.id, old_time=1.0, new_time=2.5)
        cmd.redo()

        times = [m.time for m in session_with_video.markers]
        assert times == [2.0, 2.5, 3.0]

    def test_undo_restores_original_time(self, session_with_video: EditorSession):
        """Undo moves the marker back to its original time."""
        marker = session_with_video.add_marker(1.0)
        session_with_video.undo_stack.clear()

        cmd = MoveMarkerCommand(session_with_video, marker.id, old_time=1.0, new_time=2.0)
        cmd.redo()
        cmd.undo()

        assert session_with_video.markers[0].time == 1.0

    def test_undo_maintains_sort_order(self, session_with_video: EditorSession):
        """Undo maintains markers in sorted order."""
        session_with_video.add_marker(1.0)
        marker2 = session_with_video.add_marker(2.0)
        session_with_video.undo_stack.clear()

        cmd = MoveMarkerCommand(session_with_video, marker2.id, old_time=2.0, new_time=0.5)
        cmd.redo()
        cmd.undo()

        assert session_with_video.markers[0].time == 1.0
        assert session_with_video.markers[1].time == 2.0


class TestSessionWithQUndoStack:
    """Tests for session using QUndoStack."""

    def test_add_cut_uses_undo_stack(self, session_with_video: EditorSession):
        """add_cut pushes to QUndoStack."""
        session_with_video.add_cut(1.0, 2.0)

        assert session_with_video.undo_stack.canUndo()
        assert len(session_with_video.document.edit_spec.cuts) == 1

    def test_undo_via_session_uses_undo_stack(self, session_with_video: EditorSession):
        """session.undo() uses QUndoStack for QUndoCommand commands."""
        session_with_video.add_cut(1.0, 2.0)

        session_with_video.undo()

        assert session_with_video.document.edit_spec.cuts == ()

    def test_redo_via_session_uses_undo_stack(self, session_with_video: EditorSession):
        """session.redo() uses QUndoStack for QUndoCommand commands."""
        session_with_video.add_cut(1.0, 2.0)
        session_with_video.undo()

        session_with_video.redo()

        assert len(session_with_video.document.edit_spec.cuts) == 1

    def test_multiple_commands_undo_in_order(self, session_with_video: EditorSession):
        """Multiple commands can be undone in reverse order."""
        session_with_video.add_cut(1.0, 2.0)
        session_with_video.add_cut(3.0, 4.0)

        session_with_video.undo()
        assert len(session_with_video.document.edit_spec.cuts) == 1
        assert session_with_video.document.edit_spec.cuts[0].start == 1.0

        session_with_video.undo()
        assert session_with_video.document.edit_spec.cuts == ()

    def test_set_crop_uses_undo_stack(self, session_with_video: EditorSession):
        """set_crop pushes to QUndoStack."""
        session_with_video.set_crop(10, 20, 100, 80)

        assert session_with_video.undo_stack.canUndo()
        assert session_with_video.document.edit_spec.crop == CropRect(10, 20, 100, 80)

    def test_add_marker_uses_undo_stack(self, session_with_video: EditorSession):
        """add_marker pushes to QUndoStack."""
        session_with_video.add_marker(1.5)

        assert session_with_video.undo_stack.canUndo()
        assert len(session_with_video.markers) == 1

    def test_new_command_clears_redo_stack(self, session_with_video: EditorSession):
        """Pushing a new command clears the redo stack."""
        session_with_video.add_cut(1.0, 2.0)
        session_with_video.undo()
        assert session_with_video.can_redo

        session_with_video.add_cut(3.0, 4.0)

        assert not session_with_video.undo_stack.canRedo()

    def test_undo_text_after_add_cut(self, session_with_video: EditorSession):
        """undoText is available after add_cut."""
        session_with_video.add_cut(1.5, 2.5)

        text = session_with_video.undo_stack.undoText()
        assert "1.5" in text or "Cut" in text

    def test_redo_text_after_undo(self, session_with_video: EditorSession):
        """redoText is available after undo."""
        session_with_video.add_marker(1.5)
        session_with_video.undo()

        text = session_with_video.undo_stack.redoText()
        assert "1.5" in text or "marker" in text.lower()
