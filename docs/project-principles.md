# Video Scissors Project Principles

## 1. Optimize for fast, focused video edits
Video Scissors exists to make common video edits fast and pleasant:

- remove unwanted sections
- crop the frame
- review the result immediately
- save/export when ready

The primary workflow is short, direct, and repeatable.

## 2. Keep the editing loop tight
Applying an edit should update the current working video quickly and clearly.

The app should support this rhythm:

- inspect
- scrub
- edit
- reload
- continue

Editing and exporting are separate concerns. Users should be able to perform many edits before deciding to export.

## 3. Let QML own interaction and presentation
QML should define the UI behavior:

- layout
- gestures
- direct manipulation
- visual feedback
- animations
- timeline interactions

The UI should feel native to Qt Quick and stay expressive.

## 4. Keep the Python backend small, explicit, and testable
The backend should expose narrow, intention-revealing APIs for:

- loading media metadata
- planning edits
- applying edits
- generating thumbnails
- saving/exporting results

Backend code should be easy to exercise in isolation with PyTest.

## 5. Isolate FFmpeg behind stable abstractions
FFmpeg is an implementation detail, not the architecture.

The codebase should avoid spreading FFmpeg specifics across business logic and UI integration. Media operations should be represented through small Python services with clear inputs and outputs.

## 6. Model edits explicitly
Editing behavior should be expressed through explicit domain concepts such as:

- current working video
- crop selection
- cut markers
- removable segments
- edit commands
- edit history

This keeps behavior understandable and makes testing easier.

## 7. Design for undo/redo from the start
Undo and redo are core editing capabilities, not polish.

Every editing feature should be designed with reversible actions in mind. The app should adopt a consistent command/history model early so later features do not require architectural rewrites.

## 8. Prefer thin vertical slices
Development should proceed in small, usable increments.

Each task should produce a feature that can be:

- demonstrated
- tested
- evaluated in the UI

Large infrastructure efforts should be justified by immediate feature value or by making future slices substantially simpler.

## 9. Follow the test pyramid deliberately
The project should maximize confidence while keeping feedback fast:

- many fast unit tests for editing logic and planning
- focused integration tests for FFmpeg-backed operations
- a smaller number of UI integration tests
- a minimal set of end-to-end happy-path tests

Tests should help the project evolve quickly, not slow it down.

## 10. Use TDD for backend and core editing logic
Core editing logic should usually start from tests.

In particular, TDD should drive:

- edit planning
- crop math
- marker/segment behavior
- command and undo/redo behavior
- media operation orchestration

Where UI work is highly visual, tests should still anchor important behavior even if exploration happens first.

## 11. Invest early in testing infrastructure
Good testing tools are part of the product development process.

The project should establish early support for:

- video fixtures
- fixture generation helpers
- metadata and sampled-frame assertions
- screenshot capture
- headless UI runs where possible
- reliable QML integration testing

## 12. Prefer direct manipulation over tool modes
The UI should favor immediate, obvious interactions.

Examples:

- crop by dragging directly on the video
- place cut points directly in the timeline
- remove a segment directly from the timeline affordance

Whenever possible, the user should act on the content itself rather than switch into a separate mode.

## 13. Build for polish in the timeline experience
The scrubber/timeline is a signature feature.

It should be designed as a first-class interaction surface with emphasis on:

- precise scrubbing
- visual continuity
- thumbnail quality
- responsive feedback
- strong affordances for cut operations

## 14. Keep the architecture simpler than the feature set
As features grow, the code should remain easier to understand than the UI is to use.

The project should regularly prefer:

- smaller objects
- narrower responsibilities
- explicit state
- fewer layers
- simpler naming
- clearer data flow

## 15. Treat the old project as reference material only
`~/Code/videoeditor` can be consulted for implementation ideas, experiments, and solved problems.

It does not define the target architecture for this project. Any borrowed idea should be adapted to fit the principles and architecture of Video Scissors.

## Note for agents
`~/Code/videoeditor` is reference material only.
Use it to mine isolated ideas, experiments, or implementation details.
Do not treat it as the architectural template for this project.
New code in this repository should follow this project’s principles even when the older project solved a similar problem differently.
