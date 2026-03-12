# Architecture

## Overview

Video Scissors uses a split architecture:

- **QML / Qt Quick** owns interaction and presentation
- **Python** owns editing logic and media operations

The app is centered around a tight editing loop described in `docs/vision.md`.

## Responsibilities

### QML / Qt Quick
QML should own:

- layout
- gestures
- direct manipulation
- visual feedback
- timeline behavior
- player-facing UI behavior

### Python backend
Python should own:

- editing logic
- session state
- command handling
- media operations
- orchestration around current working video

## Key architectural rules

### 1. Editing and export are separate
Editing updates the current working video inside the app.
Export is a separate save flow that writes the current working video to a chosen destination.

### 2. Undo/redo is foundational architecture
Undo/redo is part of the architecture, not polish.

All editing features must fit the chosen undo/redo model. The system should be designed so edit operations can be applied, undone, and redone consistently.

The source of truth for undo/redo lives in the Python backend, not in Qt's `QUndo` system.
The backend owns working-video history and exposes the resulting state to QML.
Qt actions may trigger undo/redo, but they should not become the architectural owner of edit history.

### 3. Keep FFmpeg behind service boundaries
FFmpeg is an implementation detail.
High-level application logic should depend on narrow backend service interfaces, not FFmpeg calls spread throughout the app.

### 4. Prefer explicit domain concepts
Model editing with clear concepts such as:

- source video
- current working video
- working-video snapshots/history
- working-video revision
- editor session
- edit commands
- crop selection
- cut markers
- removable segments

A working-video revision is a strategic identity signal.
When the working video changes, dependent UI such as thumbnails or transient overlays should react from that signal rather than from scattered imperative cleanup code.

### 5. Prefer small backend objects
Avoid large manager/processor classes that mix:

- UI plumbing
- state management
- media execution
- async coordination
- workflow orchestration
- service construction / temp-workspace setup

Prefer smaller objects with narrow responsibilities.

For example:

- `EditorSession` should own session state and history
- backend services should own media work
- `SessionBridge` should adapt and delegate for QML
- application/bootstrap code should compose concrete services and workspaces

### 6. Keep the QML/backend boundary narrow
Do not move complex workflow orchestration into a giant main QML file.
Keep the boundary intentional and easy to reason about.

QML should mostly display current backend state and react to a small number of strategic change signals.
Avoid broad fan-out patterns where one generic signal forces many imperative repairs in the UI.

## Editing-surface modeling

Direct-manipulation overlays should prefer source-video coordinates as their domain model.
For example, crop geometry should live in video-space and be rendered into the displayed video rect through a small, explicit transform.
This keeps edit requests aligned with backend coordinates and reduces repeated screen/video conversion logic.

## Feature growth guardrails

As new editing features are added, preserve the current split and resist convenience-driven drift.

- Keep backend state in Python and direct interaction in QML.
- Prefer explicit state and strategic change signals over scattered imperative UI cleanup.
- Keep `SessionBridge` as an adapter/delegator, not a composition root or feature manager.
- Prefer explicit domain objects over parallel primitive fields when a concept becomes important.
- Keep feature state in its natural domain coordinate system, then transform it for display.
- Do not build a grand generic edit framework before multiple features prove what is truly shared.
- Keep undo/redo backend-owned and scoped to committed edits.
- Prefer identity-based invalidation for async UI work before introducing heavier coordination machinery.
- Keep `Main.qml` focused on layout and simple wiring rather than workflow orchestration.

## Reference project

`~/Code/videoeditor` is reference material only.

It may be used to mine:

- implementation ideas
- experiments
- test techniques
- isolated solutions

It must not be used as the architectural template for Video Scissors.
Any borrowed idea should be adapted to this architecture.
