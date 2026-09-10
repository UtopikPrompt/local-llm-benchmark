"""HTTP controller layer.

The controller is the thin HTTP bridge between the web routes
(:mod:`local_llm_benchmark.server.app`) and the business logic in
:mod:`local_llm_benchmark.server.api.services`. It owns the HTTP concern:
request parsing, route-to-service dispatch and translating the
domain-level errors raised by the service into HTTP responses. The service
layer therefore stays agnostic of HTTP and never imports FastAPI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from local_llm_benchmark.server.api import services as services_layer
from local_llm_benchmark.server.api.services import BadRequest, EngineNotFound

# The dashboard shell and its JS/CSS assets live at the project root next to
# this package (e.g. ``web/dashboard.html``). The benchmark reports are
# written to a ``results/`` directory at the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
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

    async def results(
        self, models: str | None = None, benchmark_type: str | None = None
    ) -> Any:
        """Return filtered benchmark results from the service layer."""
        return await self._services.results(models, benchmark_type)


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
        dashboard_path = _PROJECT_ROOT / "web" / "dashboard.html"
        return FileResponse(dashboard_path)

    # Mount the static web assets (CSS, JS, images) at ``/web`` so the
    # dashboard's relative asset links resolve against the served root.
    app.mount("/web", StaticFiles(directory=_WEB_DIR))

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

    @app.get("/api/config/engines")
    async def get_all_engines_endpoint() -> dict:
        """Retrieves the list of all configured engines."""
        controller_instance = Controller()
        engines = await controller_instance.engines()
        return {"engines": engines}

    @app.get("/api/results")
    async def get_results_endpoint(
        models: str | None = None, benchmark_type: str | None = None
    ) -> Any:
        """Retrieves benchmark results based on optional filters."""
        controller_instance = Controller()
        return await controller_instance.results(models=models, benchmark_type=benchmark_type)

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
