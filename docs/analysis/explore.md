# Explore Findings: FastAPI sample_app

Concise map and key components identified during exploration of the project located at scripts/sample_app.

## Project snapshot
- scripts/sample_app/
  - app/
    - main.py
    - routers/
      - items.py
  - tests/
    - test_items.py
  - requirements.txt
  - README.md

## Notable modules and content
- app/main.py
  - FastAPI application entry point.
  - Creates app with title "sample_app" and version "0.1.0".
  - Imports and includes the items router from app.routers.items.
  - Health check endpoint at GET /health returning {"status": "ok"}.

- app/routers/items.py
  - Defines an in-memory resource router for items.
  - Creates an APIRouter with prefix /items and tag "items".
  - In-memory store: _ITEMS: dict[int, Item].
  - Item model: id: int, name: str, price: float (Pydantic BaseModel).
  - Endpoints:
    - GET /items -> list of Item objects.
    - POST /items -> create a new Item; returns 201 on success; 409 if id already exists.
    - GET /items/{item_id} -> fetch a single Item by id; 404 if not found.

- tests/test_items.py
  - Uses FastAPI TestClient with the app from app.main.
  - test_create_then_get_item: POST /items with id=1, name="widget", price=9.99 -> expect 201; then GET /items/1 -> expect 200 and name "widget".
  - test_missing_item_is_404: GET /items/999 should return 404.

- tests/test_items.py is the minimal test exercising the items router.

- scripts/sample_app/README.md
  - Running and purpose guidance for the sample app.
  - Explains the layout and how to run, including the three commands shown in the README:
    - pip install -r requirements.txt
    - uvicorn app.main:app --reload
    - pytest

- Package layout and dependencies
  - Package layout
    - The sample app is a small FastAPI package nested under scripts/sample_app/.
    - app/ is a Python package containing:
      - main.py (application entry point)
      - routers/items.py (in-memory items router)
    - tests/ contains tests/test_items.py that exercise the app.
    - README.md provides running guidance and layout notes.
  - Dependencies (scripts/sample_app/requirements.txt)
    - fastapi>=0.110
    - uvicorn[standard]>=0.29
    - pytest>=8.0
    - httpx>=0.27

- How to run (as per the provided README and code)
  - Install dependencies:
    - pip install -r requirements.txt
  - Run the FastAPI service:
    - uvicorn app.main:app --reload
  - Run tests:
    - pytest

- Notes and conventions observed
  - Structure uses a straightforward FastAPI layout:
    - app/main.py wires the application and includes routers.
    - app/routers/items.py encapsulates the items resource with an in-memory store.
    - Tests are isolated to test_items.py, using TestClient against app.main.
  - In-memory storage (_ITEMS) is used for simplicity in the sample app.
  - Endpoints follow standard HTTP semantics:
    - POST creates a resource (201) or conflicts (409).
    - GET fetches resources (200) or errors (404 for missing).
- The sample README.md consolidates quick-start guidance and documents the intended layout and commands.