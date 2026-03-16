.PHONY: run test test-gui lint typecheck check

run:
	uv run video-scissors $(FILE)

test:
	QT_QPA_PLATFORM=offscreen uv run pytest

test-gui:
	uv run pytest tests/test_gui.py -v

lint:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run ty check

check: lint typecheck test
