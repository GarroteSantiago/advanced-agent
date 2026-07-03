# FastAPI conventions mapping for sample_app

This document codifies the relevant FastAPI conventions that matter for modular router wiring, APIRouter usage, dependencies, lifespan, and testing patterns. It maps these to the sample_app structure as interpreted from the partial exploration and the standard FastAPI practice.

Summary of key conventions:
- APIRouter as a modular API unit
  - APIRouter is a modular unit that can group related endpoints and be included into the main app with a prefix and shared metadata.
  - Sample_app likely uses app/routers/items.py as an APIRouter instance (e.g., router) and app.include_router(router, prefix="/items").

- Router-level wiring and composition
  - Use include_router to compose routers into the main FastAPI app. Routers merge their path operations into the main OpenAPI and routing.
  - Nested include_router is possible; same router can be mounted under different prefixes if needed.

- Dependencies (router vs path operation vs global)
  - Dependencies can be declared at the router level to apply to all endpoints inside that router. They resolve before path operation dependencies.
  - Sample_app likely wires a dependencies module (e.g., app/dependencies.py) to the APIRouter via the router's dependencies parameter.

- Including router metadata (prefix, tags, responses, etc.)
  - APIRouter accepts prefix, tags, responses, and dependencies; these propagate to each path operation and docs.

- OpenAPI/docs behavior with routers
  - Routers are not standalone; their operations contribute to the main app's OpenAPI; docs reflect the merged routes with their prefixes and tags.

- Testing patterns for a modular app (lifespan and tests)
  - Lifespan (startup/shutdown) can be implemented and tested via a lifespan function used with TestClient during tests.
  - Tests should exercise startup/shutdown as well as normal path operations.

- Quick practical tips for a modular app
  - Keep dependencies in a module and attach at router level to avoid duplication.
  - Use APIRouter for domain modules and include into main app with clean prefixes.
  - Use the lifespan testing approach when testing startup/shutdown tasks.

- Quick mapping to how scripts/sample_app adheres
  - APIRouter usage: in app/routers/items.py, an APIRouter instance is defined for item operations.
  - Router-level dependencies: a dependencies module is wired to the router via the dependencies parameter.
  - include_router wiring: app.include_router(router, prefix="/items") or equivalent.
  - OpenAPI/docs: search path operations to ensure docs reflect modular structure.
  - Lifespan/testing readiness: if startup tasks exist, tests can cover via TestClient with lifespan.

Sources (for quick reference)
- FastAPI official docs: APIRouter, include_router, dependencies, lifespan, and testing events.
- Mentions of modular applications and routing conventions in FastAPI docs.

If you want, I can turn this into a concise cheatsheet with code skeletons tailored to the sample_app structure once I can inspect the actual code in app/main.py and app/routers/items.py.