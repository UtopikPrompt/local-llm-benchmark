"""Request and response data-transfer objects for the API.

These DTOs sit between the UI and the services. The UI posts plain JSON bodies
to the controller; the controller validates and deserializes them into these
DTOs, and the services return plain Python structures that the controller
serializes back into JSON.

The DTOs are plain dataclasses (not Pydantic models) so the API package does
not depend on Pydantic — the only shared dependency between the UI, API and
services is the core ``local_llm_benchmark`` package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RunRequest:
    """Body posted to ``POST /run``.

    Either a configured ``engine`` name is provided (selected from the
    dashboard's engine dropdown), or ``base_url``/``model`` are provided to
    build a fresh single-engine configuration.
    """

    engine: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    judge_url: Optional[str] = None
    judge_model: Optional[str] = None
    judge: Optional[str] = None
    task_dir: Optional[str] = None
    task: Optional[str] = None
    max_concurrent: Optional[int] = None
    timeout: Optional[float] = None
    trials: Optional[int] = None
    tasks: Optional[str] = None
    output: Optional[str] = None
    format: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {
            "engine": self.engine,
            "base_url": self.base_url,
            "model": self.model,
            "judge_url": self.judge_url,
            "judge_model": self.judge_model,
            "judge": self.judge,
            "task_dir": self.task_dir,
            "task": self.task,
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "trials": self.trials,
            "tasks": self.tasks,
            "output": self.output,
            "format": self.format,
        }


@dataclass
class RunResult:
    """Result of a ``POST /run`` request."""

    rows: List[Dict[str, Any]] = field(default_factory=list)
    output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {"rows": self.rows, "output": self.output}


@dataclass
class ModelsResult:
    """Result of ``POST /models``: the list of models served by an engine."""

    models: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {"models": self.models}


@dataclass
class ConfigResult:
    """Result of ``POST /config``: a preview of a candidate configuration."""

    engines: List[Dict[str, Any]] = field(default_factory=list)
    models: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {"engines": self.engines, "models": self.models}
