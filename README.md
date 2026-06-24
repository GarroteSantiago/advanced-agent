# advanced-agent

A Python project scaffold managed with [`uv`](https://docs.astral.sh/uv/) and
orchestrated through [`just`](https://github.com/casey/just).

- **Python:** 3.11.9 (pinned via `.python-version`, required `>=3.11.9`)
- **Package manager:** `uv`
- **Task runner:** `just`

## Developer artifacts

All developer tasks are exposed as `just` recipes (see `justfile`). Each one
wraps a tool through `uv run`, so no manual environment activation is needed.

| Recipe          | Command                               | Purpose                                            |
| --------------- | ------------------------------------- | -------------------------------------------------- |
| `just run`      | `uv run python main.py`               | Run the application entry point (`main.py`).       |
| `just test`     | `uv run pytest`                       | Run the test suite (`src/tests/`).                 |
| `just lint`     | `uv run ruff check --fix .`           | Lint and auto-fix with Ruff.                       |
| `just format`   | `uv run ruff format .`                | Format the codebase with Ruff.                     |
| `just type`     | `uv run pyright`                      | Static type-check with Pyright.                    |
| `just validate` | `just lint && just type && just test` | Full gate: lint, type-check, then test.            |

### Underlying tools

- **Ruff** — linter + formatter (config in `pyproject.toml`; line length 110,
  curated rule set, double quotes).
- **Pyright** — static type checker.
- **pytest** — test framework.

## Project layout

```
.
├── main.py                  # Application entry point
├── justfile                 # Developer task recipes
├── pyproject.toml           # Project metadata + tool config (ruff)
├── uv.lock                  # Locked dependency graph
├── .python-version          # Pinned Python (3.11.9)
└── src/
    ├── advanced_agent/      # Package source
    └── tests/               # Test suite
```

## Installation

Requires [`uv`](https://docs.astral.sh/uv/getting-started/installation/) and
[`just`](https://github.com/casey/just#installation).

```sh
# 1. Clone
git clone <repository-url>
cd advanced-agent

# 2. Create the virtualenv and install all (incl. dev) dependencies
uv sync
```

`uv sync` provisions Python 3.11.9 if needed and installs the locked
dependency set from `uv.lock`.

## Running

```sh
just run        # or: uv run python main.py
```

## Validating changes

Before committing, run the full gate:

```sh
just validate   # lint --fix, type-check, test
```
