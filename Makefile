.PHONY: run test test-gui

run:
	uv run video-scissors

test:
	QT_QPA_PLATFORM=offscreen uv run pytest

test-gui:
	uv run pytest tests/test_gui.py -v
