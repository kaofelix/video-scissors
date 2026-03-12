.PHONY: run test test-gui test-headless

run:
	uv run video-scissors

test:
	uv run pytest

test-gui:
	uv run pytest tests/test_gui.py -v

test-headless:
	QT_QPA_PLATFORM=offscreen uv run pytest -v
