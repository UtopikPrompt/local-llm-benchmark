"""HTTP controller layer.

The controller is the thin HTTP bridge between the web routes and the business
logic in :mod:`local_llm_benchmark.src.api.services`. It owns the HTTP
concern:
request parsing, route-to-service dispatch and translating the
domain-level errors raised by the service into HTTP responses. The service
layer therefore stays agnostic of HTTP and never imports FastAPI.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer

from local_llm_benchmark.config import EngineConfig
from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine
from local_llm_benchmark.logger import BenchmarkLogger, logger
from local_llm_benchmark.schemas.engine import EngineConfig, EngineResult
from local_llm_benchmark.schemas.response import LLMResponse, Choice
from local_llm_benchmark.schemas.request_schemas import (
    EnginePreviewRequest,
    EngineSaveRequest,
    EngineUpdateRequest,
    ModelListRequest,
    RunRequest,
)
from local_llm_benchmark.schemas.response import BenchmarkResultsResponse
from local_llm_benchmark.server.api import services as services_layer
from local_llm_benchmark.server.api.services import BadRequest, EngineNotFound
from local_llm_benchmark.auth import get_current_user

# OAuth2 security scheme for JWT authentication
security_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scopes={
        "admin": "Full system access",
        "benchmarker": "Can run benchmarks",
        "viewer": "Read-only access"
    }
)

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
        self._config_path: Path | None = None

    async def defaults(self) -> None:
        """Return the centralized defaults used to seed the dashboard form."""
        await self._require_auth()
        logger.info("Controller defaults requested")
        return await self._services.defaults()

    async def engines(self) -> None:
        """Return the engines configured in the dashboard's config file."""
        await self._require_auth()
        logger.info("Controller engines requested", extra={"config_path": str(self._config_path) if self._config_path else None})
        return await self._services.engines(self._config_path)

    async def run(self, request: RunRequest) -> None:
        """Run the benchmark described by *request* and return the rows."""
        await self._require_auth()
        logger.info("Controller run requested", extra={"model": request.model, "max_tokens": request.max_tokens, "timeout": request.timeout})
        try:
            return await self._services.run(request)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            logger.warning("EngineNotFound from service", extra={"engine": request.model})
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def config(self, base_url: str, model: str) -> None:
        """Preview a candidate configuration and the models it serves."""
        await self._require_auth()
        logger.info("Controller config requested", extra={"base_url": base_url, "model": model})
        engine = _build_engine("preview", base_url, model)
        models = await engine.list_models()
        await engine.close()
        return {
            "engines": [{"name": "preview", "base_url": base_url, "model": model}],
            "models": models,
        }

    async def models(self, base_url: str) -> None:
        """List models available on the engine at *base_url*."""
        await self._require_auth()
        logger.info("Controller models requested", extra={"base_url": base_url})
        engine = _build_engine("models", base_url, "")
        models = await engine.list_models()
        await engine.close()
        return {"models": models}
        engine = _build_engine("models", base_url, "")
        models = await engine.list_models()
        await engine.close()
        return {"models": models}

    async def results(self, models: str | None = None, benchmark_type: str | None = None) -> Any:
        """Return filtered benchmark results from the service layer."""
        await self._require_auth()
        logger.info("Controller results requested", extra={"models": models, "benchmark_type": benchmark_type})
        return await self._services.results(models, benchmark_type)
        return await self._services.results(models, benchmark_type)

    async def save_engine(self, request: EngineSaveRequest) -> None:
        """Persist a new engine to the config file and return it as a mapping."""
        await self._require_auth()
        logger.info("Controller save_engine requested", extra={"engine_name": request.name, "base_url": request.base_url, "model": request.model})
        try:
            return await self._services.save_engine(request, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            return await self._services.save_engine(request, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def get_engine(self, name: str) -> None:
        """Return the engine mapping for *name*, or raise ``EngineNotFound``."""
        await self._require_auth()
        logger.info("Controller get_engine requested", extra={"engine_name": name})
        try:
            return await self._services.get_engine(name, self._config_path)
        except EngineNotFound as exc:
            logger.warning("EngineNotFound from service", extra={"engine": name})
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        try:
            return await self._services.get_engine(name, self._config_path)
        except EngineNotFound as exc:
            logger.warning("EngineNotFound from service", extra={"engine": name})
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def update_engine(self, name: str, request: EngineUpdateRequest) -> None:
        """Replace the engine *name* in the config file and return it as a mapping."""
        await self._require_auth()
        logger.info("Controller update_engine requested", extra={"engine_name": name, "base_url": request.base_url, "model": request.model})
        try:
            return await self._services.update_engine(name, request, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        try:
            return await self._services.update_engine(name, request, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def delete_engine(self, name: str) -> Any:
        """Remove the engine *name* from the config file and return its name."""
        logger.info("Controller delete_engine requested", extra={"engine_name": name})
        try:
            return await self._services.delete_engine(name, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            logger.warning("EngineNotFound from service", extra={"engine": name})es.delete_engine(name, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            logger.warning("EngineNotFound from service", extra={"engine": name})es.delete_engine(name, self._config_path)
        except BadRequest as exc:
            logger.warning("BadRequest from service", extra={"detail": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineNotFound as exc:
            logger.warning("EngineNotFound from service", extra={"engine": name})
            raise HTTPException(status_code=404, detail=str(exc)) from exc


def _build_engine(name: str, base_url: str, model: str) -> Any:
    """Build a concrete engine used only to preview its advertised models."""
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
        data = load_config(str(path), str(path))
        Defaults.engines = list(data.engines)
        _controller._config_path = path

    app = app or FastAPI(title="Local LLM Benchmark", version="0.1.0")

    # The dashboard HTML is the front door. Register an explicit ``/`` route
    # first so the dashboard always wins; the static handler below only
    # answers the remaining asset requests inside the web directory.
    @app.get("/", response_model=None)
    async def index() -> FileResponse:
        """Serve the dashboard HTML shell."""
        dashboard_path = _PROJECT_ROOT / "web" / "dashboard.html"
        return FileResponse(dashboard_path)

    # Mount the static web assets (CSS, JS, images) at ``/web`` so the
    # dashboard's relative asset links resolve against the served root.
    app.mount("/web", StaticFiles(directory=_WEB_DIR))

    @app.get("/api/defaults", response_model=None)
    async def defaults() -> Any:
        """Return the centralized defaults used to seed the dashboard form."""
        return await _controller.defaults()

    @app.post("/api/config", response_model=None)
    async def config(request: EnginePreviewRequest) -> None:
        """Preview a candidate configuration and the models it serves."""
        return await _controller.config(request.base_url, request.model)

    @app.post("/api/models", response_model=None)
    async def models(request: ModelListRequest) -> None:
        """List models available on the engine at *base_url*."""
        return await _controller.models(request.base_url)

    @app.post("/api/run", response_model=None)
    async def run(request: RunRequest) -> Any:
        """Run the benchmark described by *request* and return the rows."""
        return await _controller.run(request)

    @app.get("/api/results/{name}", response_model=BenchmarkResultsResponse)
    async def results(name: str) -> BenchmarkResultsResponse:
        """Stream a saved report named *name*."""
        return await _controller.results(name)

    @app.get("/api/engines", response_model=None)
    async def engines() -> None:
        """Return the engines configured in the dashboard's config file."""
        return await _controller.engines()

    @app.get("/api/config/engines", response_model=None)
    async def api_engines() -> Any:
        """Return the list of configured engines."""
        return {"engines": await _controller.engines()}

    @app.post("/api/config/engines", response_model=None)
    async def api_save_engine(request: EngineSaveRequest) -> Any:
        """Persist a new engine to the config file."""
        return await _controller.save_engine(request)

    @app.get("/api/config/engines/{name}", response_model=None)
    async def api_get_engine(name: str) -> None:
        """Return the configured engine *name*."""
        return await _controller.get_engine(name)

    @app.put("/api/config/engines/{name}")
    async def api_update_engine(name: str, request: EngineUpdateRequest) -> Any:
        """Replace the configured engine *name* in the config file."""
        return await _controller.update_engine(name, request)

    @app.delete("/api/config/engines/{name}")
    async def api_delete_engine(name: str) -> Any:
        """Remove the configured engine *name* from the config file."""
        return await _controller.delete_engine(name)

    @app.get("/api/tasks", response_model=None)
    async def api_tasks() -> Any:
        """Return the default task corpus."""
        return {"tasks": await _controller._services.tasks()}

    @app.get("/api/results", response_model=None)
    async def api_results(models: str | None = None, benchmark_type: str | None = None) -> Any:
        """Return filtered benchmark results for the dashboard table."""
        models_list = [m.strip() for m in models.split(",")] if models else None
        return await _controller.results(models_list, benchmark_type)

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the web server until interrupted."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)


def _resolve_config(config_path: str) -> Path:
    from pathlib import Path

    return Path(config_path)
