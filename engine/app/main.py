"""FastAPI application entrypoint for the local LLM benchmark."""
from __future__ import annotations

from fastapi import FastAPI

from app.storage.db import init_db

app = FastAPI(title="Local LLM Benchmark", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    """Initialise storage when the application boots."""
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness probe used by the health test suite."""
    return {"status": "ok"}