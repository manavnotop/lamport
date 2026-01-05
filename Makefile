.PHONY: fix install lint test

install:
	uv sync

fix:
	uv run ruff check --select I --fix .
	uv run ruff format .

lint:
	uv run ruff check .
	uv run ruff format --check .

run: 
	uv run src/main.py