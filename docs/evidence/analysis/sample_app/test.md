# Test insights for scripts/sample_app

Summary of tests and what remains:

- Tests live in scripts/sample_app/tests/test_items.py and exercise a FastAPI app defined in scripts/sample_app/app.
- Observations from partial testing notes:
  - The app exposes an in-memory items store via an APIRouter (GET /items, POST /items, GET /items/{id}) and a health endpoint at /health.
  - Running pytest from the repo root initially failed to import the app due to Python not finding the module path (ModuleNotFoundError: No module named 'app').
  - Adjusting PYTHONPATH to include scripts/sample_app resolves the import problem; with PYTHONPATH=scripts/sample_app, tests run and both tests pass: 2 tests, 2 passed.
  - The tests rely on an in-memory store; test order could affect results in some setups, but current tests pass.

- Unresolved/blocked:
  - Running tests without modifying PYTHONPATH is blocked in a fresh environment.
  - How CI should run these tests without needing manual PYTHONPATH adjustment (e.g., packaging or pytest config).

- Suggested commands (typical local run):
  - PYTHONPATH=scripts/sample_app pytest
  - Alternatively, install the package or set up editable install and run: pip install -e . in scripts/sample_app (if a setup.cfg/setup.py exists) and then pytest

- Quick test coverage notes:
  - test_create_then_get_item: POST /items with id=1, then GET /items/1 and verify name
  - test_missing_item_is_404: GET /items/999 should return 404

If you’d like, I can extend this with concrete code snippets for the test client usage and packaging steps.