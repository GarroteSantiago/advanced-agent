"""FastAPI application entry point for the sample service."""

from fastapi import FastAPI

from app.routers import items

app = FastAPI(title="sample_app", version="0.1.0")
app.include_router(items.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
