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

### 3. Keep FFmpeg behind service boundaries
FFmpeg is an implementation detail.
High-level application logic should depend on narrow backend service interfaces, not FFmpeg calls spread throughout the app.

### 4. Prefer explicit domain concepts
Model editing with clear concepts such as:

- source video
- current working video
- editor session
- edit commands
- crop selection
- cut markers
- removable segments

### 5. Prefer small backend objects
Avoid large manager/processor classes that mix:

- UI plumbing
- state management
- media execution
- async coordination
- workflow orchestration

Prefer smaller objects with narrow responsibilities.

### 6. Keep the QML/backend boundary narrow
Do not move complex workflow orchestration into a giant main QML file.
Keep the boundary intentional and easy to reason about.

## Reference project

`~/Code/videoeditor` is reference material only.

It may be used to mine:

- implementation ideas
- experiments
- test techniques
- isolated solutions

It must not be used as the architectural template for Video Scissors.
Any borrowed idea should be adapted to this architecture.
