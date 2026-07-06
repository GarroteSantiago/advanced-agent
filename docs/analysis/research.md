# Research Findings: FastAPI conventions and modular routing (partial)

This file consolidates the synthesis from the Researcher agent about FastAPI conventions relevant to the sample_app structure and modular routing. It captures what is commonly expected in a clean FastAPI project and what remains ambiguous in the provided materials.

Key conventions and patterns observed
- APIRouter as a modular router unit
  - APIRouter is designed to host its own path operations, dependencies, and metadata, and then be mounted into a FastAPI app via include_router. This allows modular grouping of endpoints (e.g., items, users) under prefixes and tags.
  - Example patterns in typical projects:
    - api_router = APIRouter(prefix="/items", tags=["items"])
    - @api_router.get("/") -> list items
    - app.include_router(api_router)

- include_router wiring and mounting routers
  - The recommended approach is to include sub-routers into the main app, merging their paths, not mounting as separate apps. Prefixes order and path operations are preserved.
  - It is common to have multiple routers (e.g., users, items) and mount them with distinct prefixes (e.g., /users, /items).

- router-level vs global dependencies
  - Both router-level dependencies (declared on the APIRouter) and global app-level dependencies can be used.
  - Dependency execution order typically: router dependencies first, then path operation dependencies, then other parameter dependencies. This enables patterns like shared authentication or validation at the router level.

- startup/shutdown lifespans (lifespan events)
  - There is broad mention of startup/shutdown sequences but concrete, per-router lifecycle hooks are not deeply standardized in the provided materials.
  - For pure app-level startup/shutdown, FastAPI supports @app.on_event("startup") and @app.on_event("shutdown"), or lifespan context. Per-router startup hooks are more nuanced and not standard in the minimal tutorials.

- testing patterns
  - Testing FastAPI apps using TestClient (HTTPX) with pytest is standard.
  - Tests typically import the app (from app.main import app) and perform requests via TestClient, asserting responses.

- alignment with the sample_app structure
  - The provided structure (app/main.py, app/routers/items.py, tests/test_items.py) aligns with common modular routing patterns described above.

Remaining questions and gaps (as observed)
- Per-router startup/shutdown hooks: canonical patterns for router-scoped startup hooks are not well-documented in the supplied materials.
- Pyproject.toml entrypoint patterns: unclear how universal the entrypoint-based startup is across samples; the minimal example may omit pyproject.toml in some contexts.
- Deeper cross-router testing strategies: limited coverage in the cited materials for integrated tests across multiple routers.

Summary of actionable guidance based on the observed conventions
- Use APIRouter for modular routing and include_router in the main app to compose the API.
- Prefer router-level dependencies for cross-cutting concerns like authentication, and rely on global app dependencies for application-wide concerns.
- Use TestClient for unit and integration tests, ensuring the Python path is configured so that from app.main import app resolves in tests.

Cited references used for synthesis
- APIRouter patterns and include_router wiring: typical FastAPI modular routing resources and tutorials (general conventions).
- Testing patterns with TestClient and pytest: standard FastAPI testing approach.

Notes
- This document reflects partially observed conventions and notes gaps where the targeted samples do not provide explicit patterns. If you want, I can extend this with concrete code snippets and a starter template that follows these conventions.