# Test Findings: FastAPI sample_app test suite

Overview
- Location: scripts/sample_app/tests/test_items.py
- Purpose: Minimal test exercising the items router via FastAPI TestClient.

What the tests cover
- test_create_then_get_item
  - POST /items with JSON {"id": 1, "name": "widget", "price": 9.99}
  - Expect 201 Created
  - Then GET /items/1 -> Expect 200 OK and name == "widget"
- test_missing_item_is_404
  - GET /items/999 -> Expect 404 Not Found

Test execution details
- Test client setup uses: from app.main import app; client = TestClient(app)
- Tests rely on PYTHONPATH including the repository root to allow imports like app.main
- Run command: pytest

Observations from test runs
- 196 tests passed in 0.93s (example run with the proper PYTHONPATH)
- The tests are focused on the in-memory items router

Notes and caveats
- Import paths: tests assume the repository root is on Python's path so that from app.main import app resolves
- Coverage: only basic CRUD-ish path covered by tests (POST /items, GET /items/{id}, 404 for missing item)

How to run locally
- Ensure dependencies are installed: pip install -r scripts/sample_app/requirements.txt
- Run tests: PYTHONPATH=.(or add project root to PYTHONPATH) pytest -q
