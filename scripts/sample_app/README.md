# sample_app

A deliberately small FastAPI service used as a **fixed analysis target** for the
advanced-agent demo (`scripts/analyze_repo.py`). It is not meant to be deployed;
it exists so the agent's five subagents have a real, self-contained repository to
explore, research, and check.

## Layout

- `app/main.py` — the FastAPI application and its router wiring.
- `app/routers/items.py` — a single resource router (in-memory store).
- `tests/test_items.py` — a minimal test exercising the router.
- `requirements.txt` — declared dependencies.

## Running

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```
