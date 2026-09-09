"""HTTP controller layer.

The controller is the thin HTTP bridge between the web routes
(:mod:`local_llm_benchmark.web.app`) and the business logic in
:mod:`local_llm_benchmark.web.api.services`. It owns the HTTP concern:
request parsing, route-to-service dispatch and translating the
domain-level errors raised by the service into HTTP responses. The service
layer therefore stays agnostic of HTTP and never imports FastAPI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from local_llm_benchmark.web.api import services as services_layer
from local_llm_benchmark.web.api.services import BadRequest, EngineNotFound
from local_llm_benchmark.web import static as static_layer

# The dashboard shell and its JS/CSS assets live alongside the package at
# ``src/web`` (e.g. ``src/web/dashboard.html``). The benchmark reports are
# written to a ``results/`` directory at the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_WEB_DIR = _PROJECT_ROOT / "web"
_RESULTS_DIR = _PROJECT_ROOT / "results"


class Controller:
    """Dispatch HTTP endpoints to the service layer and map its errors."""

    def __init__(self) -> None:
        self._services = services_layer

    async def defaults(self) -> Any:
        """Return the centralized defaults used to seed the dashboard form."""
        return await self._services.defaults()

    async def engines(self) -> Any:
        """Return the engines configured in the dashboard's config file."""
        return await self._services.engines()

    async def run(self, request: dict) -> Any:
        """Run the benchmark described by *request* and return the rows."""
        try:
            return await self._services.run(request)
        except BadRequest as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def config(self, base_url: str, model: str) -> Any:
        """Preview a candidate configuration and the models it serves."""
        engine = _build_engine("preview", base_url, model)
        models = await engine.list_models()
        await engine.close()
        return {
            "engines": [{"name": "preview", "base_url": base_url, "model": model}],
            "models": models,
        }

    async def models(self, base_url: str) -> Any:
        """List models available on the engine at *base_url*."""
        engine = _build_engine("models", base_url, "")
        models = await engine.list_models()
        await engine.close()
        return {"models": models}

    async def results(self, name: str) -> Any:
        """Stream a saved report named *name* from the ``results/`` directory."""
        try:
            target = static_layer.resolve(_RESULTS_DIR, name)
        except static_layer.NotFound:
            raise HTTPException(status_code=404, detail=f"report '{name}' not found") from None
        if target.suffix == ".json":
            return FileResponse(target, media_type="application/json")
        return FileResponse(target, media_type="text/csv")


def _build_engine(name: str, base_url: str, model: str) -> Any:
    """Build a concrete engine used only to preview its advertised models."""
    from local_llm_benchmark.config import EngineConfig
    from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

    return OpenAICompatEngine(EngineConfig(name=name, base_url=base_url, model=model))


app = FastAPI(title="Local LLM Benchmark API", version="0.1.0")
_controller = Controller()


def create_app(config_path: str | None = None, app: FastAPI | None = None) -> FastAPI:
    """Build the FastAPI application.

    *config_path* points at a configuration file whose engines are loaded into
    ``Defaults.engines`` so the dashboard's engine dropdown and the ``/run``
    multi-engine selection use them. Defaults to the project-root ``config.yaml``
    when present.

    An optional *app* may be passed in; the caller registers the ``/`` front
    door route before the static handler is mounted at ``/`` so the dashboard
    HTML always wins over asset requests.
    """
    from local_llm_benchmark.config import Defaults, load_config, project_config_path

    config_path = config_path or str(project_config_path())
    path = _resolve_config(config_path)
    if path.exists():
        data = load_config(str(path))
        Defaults.engines = list(data.engines)

    app = app or FastAPI(title="Local LLM Benchmark", version="0.1.0")

    # The dashboard HTML is the front door. Register an explicit ``/`` route
    # first so the dashboard always wins; the static handler below only
    # answers the remaining asset requests inside the web directory.
    @app.get("/")
    async def index() -> FileResponse:
        """Serve the dashboard HTML shell."""
        return FileResponse(_WEB_DIR / "dashboard.html", media_type="text/html")

    # The dashboard and its assets live alongside the package at ``src/web``.
    static_layer.install(app, _WEB_DIR)

    @app.get("/defaults")
    async def defaults() -> Any:
        """Return the centralized defaults used to seed the dashboard form."""
        return await _controller.defaults()

    @app.post("/config")
    async def config(base_url: str, model: str) -> Any:
        """Preview a candidate configuration and the models it serves."""
        return await _controller.config(base_url, model)

    @app.post("/models")
    async def models(base_url: str) -> Any:
        """List models available on the engine at *base_url*."""
        return await _controller.models(base_url)

    @app.post("/run")
    async def run(request: dict) -> Any:
        """Run the benchmark described by *request* and return the rows."""
        return await _controller.run(request)

    @app.get("/results/{name}")
    async def results(name: str) -> Any:
        """Stream a saved report named *name*."""
        return await _controller.results(name)

    @app.get("/engines")
    async def engines() -> Any:
        """Return the engines configured in the dashboard's config file."""
        return await _controller.engines()

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the web server until interrupted."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)


def _resolve_config(config_path: str) -> Any:
    from pathlib import Path

    path = Path(config_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"configuration file not found: {path}")
    return path
