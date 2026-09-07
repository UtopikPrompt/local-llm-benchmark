"""FastAPI web server: JSON API + static dashboard.

The browser is a *display* concern, not a *compute* concern: this server renders
results and all heavy work (benchmarking) happens in :mod:`local_llm_benchmark.runner`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from local_llm_benchmark.config import BenchmarkConfig, EngineConfig, JudgeConfig
from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine
from local_llm_benchmark.report.report import write_report
from local_llm_benchmark.results import Row
from local_llm_benchmark.runner import run_benchmark

# The dashboard template.
_DASHBOARD = Path(__file__).parent / "dashboard.html"


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="Local LLM Benchmark", version="0.1.0")

    @app.get("/")
    async def index() -> FileResponse:
        """Serve the dashboard."""
        return FileResponse(_DASHBOARD, media_type="text/html")

    @app.post("/config")
    async def config(base_url: str, model: str) -> JSONResponse:
        """List engines and models for a candidate configuration.

        Returns a preview of what a configuration with this engine would look
        like, including the models the engine advertises.
        """
        engine = EngineConfig(name="preview", base_url=base_url, model=model)
        engine_obj = OpenAICompatEngine(engine)
        models = await engine_obj.list_models()
        await engine_obj.close()
        return JSONResponse({"engines": [{"name": "preview", "base_url": base_url, "model": model}], "models": models})

    @app.post("/models")
    async def models(base_url: str) -> JSONResponse:
        """List models available on the engine at *base_url*."""
        engine = EngineConfig(name="models", base_url=base_url, model="")
        engine_obj = OpenAICompatEngine(engine)
        models = await engine_obj.list_models()
        await engine_obj.close()
        return JSONResponse({"models": models})

    @app.post("/run")
    async def run(request: dict) -> JSONResponse:
        """Run the benchmark and return the result rows.

        Accepts a JSON body with keys ``base_url``, ``model``, ``judge_url``,
        ``judge_model``, ``task_dir``, ``task``, ``max_concurrent``, ``timeout``,
        ``trials``, ``output`` and ``format``. Also writes a CSV/JSON report.
        """
        base_url = request.get("base_url")
        model = request.get("model")
        if not base_url or not model:
            raise HTTPException(status_code=400, detail="'base_url' and 'model' are required")
        engine = EngineConfig(name="ollama", base_url=base_url, model=model, timeout=request.get("timeout", 60.0), max_concurrent=request.get("max_concurrent", 1))
        judges: List[JudgeConfig] = []
        judge_url = request.get("judge_url") or request.get("judgeUrl")
        if judge_url:
            judges.append(JudgeConfig(name="judge", base_url=str(judge_url), model=request.get("judge_model") or request.get("judgeModel") or "judge", timeout=request.get("timeout", 60.0)))
        config = BenchmarkConfig(
            engines=[engine],
            judges=judges,
            tasks=request.get("task_dir", "."),
            task=request.get("task"),
            max_concurrent=request.get("max_concurrent", 1),
            timeout=request.get("timeout", 60.0),
            format=request.get("format", "json"),
            output=request.get("output", "results.json"),
        )
        rows = await run_benchmark(config)
        write_report(rows, config.output, fmt=request.get("format", "json"))
        return JSONResponse({"rows": [row.to_dict() for row in rows], "output": config.output})

    @app.get("/results/{name}")
    async def results(name: str) -> FileResponse:
        """Stream a saved report named *name*."""
        path = Path("results") / name
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"report '{name}' not found")
        if path.suffix == ".json":
            return FileResponse(path, media_type="application/json")
        return FileResponse(path, media_type="text/csv")

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the web server until interrupted."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)
