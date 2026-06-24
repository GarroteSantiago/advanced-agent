run:
    uv run python main.py

test:
    uv run pytest

lint:
    uv run ruff check .

format:
    uv run ruff format .

type:
    uv run pyright

validate:
    just lint
    just type
    just test
