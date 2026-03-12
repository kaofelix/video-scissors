# Agents Guide

## Planning

Use **dex** as the source of truth for planning and execution.

- Track work in dex.
- Do not keep parallel markdown plans or TODO lists.
- If planning starts in markdown, move the important details into dex and remove the planning file.
- Read the relevant dex task and parent context before starting meaningful work.

## Testing

Follow the test pyramid deliberately:

- fast unit tests for editing logic
- focused integration tests for FFmpeg-backed behavior
- a smaller number of UI integration tests
- a minimal end-to-end happy-path suite

Prefer TDD for backend and core editing logic.
Keep business logic testable without Qt where possible.

## Reference project

`~/Code/videoeditor` is reference material only.

Use it to mine ideas, experiments, and isolated implementation techniques.
Do not use it as the architectural template for this repository.
Any borrowed idea must be adapted to Video Scissors principles and architecture.

## Repo docs

- `docs/vision.md` contains product and UX direction.
- `docs/project-principles.md` contains the project principles.
- `docs/architecture.md` contains the architecture guidance.
- dex contains the active plan and task breakdown.
