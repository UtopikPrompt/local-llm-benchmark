"""HTTP layer for the API.

FastAPI handles the HTTP concerns (routing, request parsing, JSON responses)
natively, so this module is a thin bridge: it wires the HTTP endpoints to the
functions in :mod:`api.services`, which own the business logic.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from local_llm_benchmark.web.api import services
from local_llm_benchmark.web.api import models


def create_app(config_path: str | None = None) -> FastAPI:
    """Build the FastAPI application.

    *config_path* points at a configuration file whose engines are loaded into
    ``Defaults.engines`` so the dashboard's engine dropdown and the ``/run``
    multi-engine selection use them. Defaults to the project-root ``config.yaml``
    when present.
    """
    from local_llm_benchmark.config import Defaults, load_config, project_config_path

    config_path = config_path or str(project_config_path())
    path = _resolve_config(config_path)
    if path.exists():
        data = load_config(str(path))
        Defaults.engines = list(data.engines)

    app = FastAPI(title="Local LLM Benchmark API", version="0.1.0")

    @app.get("/defaults")
    async def defaults() -> Any:
        """Return the centralized default values used to seed the dashboard form."""
        return await services.defaults()

    @app.post("/config")
    async def config(base_url: str, model: str) -> Any:
        """Preview a candidate configuration and the models it serves."""
        engine = models.EngineConfig(name="preview", base_url=base_url, model=model)
        engine_obj = _new_engine(engine)
        models_available = await engine_obj.list_models()
        await engine_obj.close()
        return {
            "engines": [{"name": "preview", "base_url": base_url, "model": model}],
            "models": models_available,
        }

    @app.post("/models")
    async def models(base_url: str) -> Any:
        """List models available on the engine at *base_url*."""
        engine = models.EngineConfig(name="models", base_url=base_url, model="")
        engine_obj = _new_engine(engine)
        models_available = await engine_obj.list_models()
        await engine_obj.close()
        return {"models": models_available}

    @app.post("/run")
    async def run(request: dict) -> Any:
        """Run the benchmark described by *request* and return the result rows."""
        return await services.run(request)

    @app.get("/results/{name}")
    async def results(name: str) -> Any:
        """Stream a saved report named *name*."""
        from pathlib import Path

        path = Path("results") / name
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"report '{name}' not found")
        if path.suffix == ".json":
            return path
        return path

    @app.get("/engines")
    async def engines() -> Any:
        """Return the engines configured in the dashboard's config file."""
        return await services.engines()

    return app


def _new_engine(engine: models.EngineConfig) -> Any:
    from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    return OpenAICompatEngine(engine)


def _resolve_config(config_path: str) -> Any:
    from pathlib import Path

    path = Path(config_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"configuration file not found: {path}")
    return path
