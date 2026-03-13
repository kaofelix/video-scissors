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

## Tooling

- Use `ruff` for linting
- Use `ruff format` for formatting
- Use `ty` for type checking

## Development workflow

Run the app:
```
make run
```

Run tests (headless by default):
```
make test
```

Run GUI tests with visible window (useful for debugging):
```
make test-gui
```

Run all checks (lint, typecheck, test):
```
make check
```

### Test fixtures

Video fixtures are generated on the fly using FFmpeg's `testsrc` filter. No external video files needed. See `tests/conftest.py` for:
- `test_video` fixture - 320x240, 2 seconds
- `generate_test_video()` helper for custom dimensions/durations

### Screenshot capture

GUI tests can capture screenshots for debugging:
```python
def test_something(app_window, capture_screenshot):
    # ... set up state ...
    capture_screenshot(app_window, "my_test_name")
```

Screenshots are saved to `tests/screenshots/` (gitignored).
