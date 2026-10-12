"""FastAPI application entrypoint for the local LLM benchmark backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.storage.db import init_db

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Initialize the storage layer when the server starts."""
    settings: Settings = get_settings()
    logger.info(
        "starting engine",
        extra={
            "data": {
                "event": "startup",
                "database_path": settings.database_path,
            }
        },
    )
    init_db(settings.database_path)
    yield
    logger.info(
        "shutting down engine",
        extra={"data": {"event": "shutdown"}},
    )


app = FastAPI(
    title="Local LLM Benchmark Engine",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe.

    ``{"status": "ok"}`` when the service is up. The acceptance test asserts on
    this exact body, so keep the contract stable.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", reload=True, port=8000)
