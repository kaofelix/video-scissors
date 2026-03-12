.PHONY: run test

run:
	uv run video-scissors

test:
	uv run pytest
