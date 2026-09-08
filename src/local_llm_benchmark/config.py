"""Configuration for the benchmark.

Defines the data classes used to describe engines, judges and benchmark
parameters, and helpers to parse / read / write YAML or JSON configuration
files.

A configuration file is either JSON or YAML. Because JSON is a subset of YAML,
the loader sniffs the format by trying ``json.loads`` first and falling back to
YAML.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml


class ConfigError(ValueError):
    """Raised when a configuration is invalid."""


class EngineConfig:
    """Configuration of a single engine under test.

    Attributes:
        name: Unique, human-readable name of the engine.
        base_url: Absolute ``http(s)`` base URL of the OpenAI-compatible engine.
        model: Name/identifier of the model served by the engine.
        timeout: Per-request timeout in seconds (must be positive).
        max_concurrent: Maximum number of concurrent requests per task (integer).
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        *,
        timeout: float = 60.0,
        max_concurrent: int = 1,
    ) -> None:
        self.name = name
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineConfig":
        """Build an :class:`EngineConfig` from a mapping."""
        if not isinstance(data, dict):
            raise ConfigError("engine entry must be a mapping")
        name = data.get("name")
        base_url = data.get("base_url")
        model = data.get("model")
        if not name or not isinstance(name, str):
            raise ConfigError("engine 'name' is required and must be a string")
        if not base_url or not isinstance(base_url, str):
            raise ConfigError(f"engine '{name}' is missing a 'base_url'")
        if not model or not isinstance(model, str):
            raise ConfigError(f"engine '{name}' is missing a 'model'")
        if not _is_absolute_http_url(base_url):
            raise ConfigError(
                f"engine '{name}' has an invalid base_url: '{base_url}' "
                "(must be an absolute http(s) URL)"
            )
        timeout = data.get("timeout", 60.0)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            raise ConfigError(f"engine '{name}' has an invalid timeout: '{timeout}'")
        max_concurrent = data.get("max_concurrent", 1)
        if not isinstance(max_concurrent, int) or isinstance(max_concurrent, bool) or max_concurrent < 1:
            raise ConfigError(
                f"engine '{name}' has an invalid max_concurrent: '{max_concurrent}'"
            )
        return cls(name, base_url, model, timeout=timeout, max_concurrent=max_concurrent)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "max_concurrent": self.max_concurrent,
        }

    def __eq__(self, other: object) -> bool:  # noqa: E501
        if not isinstance(other, EngineConfig):
            return NotImplemented
        return (
            self.name == other.name
            and self.base_url == other.base_url
            and self.model == other.model
            and self.timeout == other.timeout
            and self.max_concurrent == other.max_concurrent
        )

    def __repr__(self) -> str:  # noqa: E501
        return (
            f"EngineConfig(name={self.name!r}, base_url={self.base_url!r}, "
            f"model={self.model!r}, timeout={self.timeout!r}, "
            f"max_concurrent={self.max_concurrent!r})"
        )


class JudgeConfig:
    """Configuration of an optional judge model used for quality scoring."""

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        *,
        timeout: float = 60.0,
    ) -> None:
        self.name = name
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JudgeConfig":
        """Build a :class:`JudgeConfig` from a mapping."""
        if not isinstance(data, dict):
            raise ConfigError("judge entry must be a mapping")
        name = data.get("name")
        base_url = data.get("base_url")
        model = data.get("model")
        if not name or not isinstance(name, str):
            raise ConfigError("judge 'name' is required and must be a string")
        if not base_url or not isinstance(base_url, str):
            raise ConfigError(f"judge '{name}' is missing a 'base_url'")
        if not model or not isinstance(model, str):
            raise ConfigError(f"judge '{name}' is missing a 'model'")
        if not _is_absolute_http_url(base_url):
            raise ConfigError(f"judge '{name}' has an invalid base_url: '{base_url}'")
        timeout = data.get("timeout", 60.0)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            raise ConfigError(f"judge '{name}' has an invalid timeout: '{timeout}'")
        return cls(name, base_url, model, timeout=timeout)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
        }


class BenchmarkConfig:
    """Top-level benchmark configuration.

    Attributes:
        engines: List of engines under test.
        judges: Optional list of judge models.
        tasks: Path to the task corpus (directory of YAML/JSON task files).
        task: Optional single task id to run.
        max_concurrent: Maximum concurrent engine requests globally.
        timeout: Default per-request timeout in seconds.
        format: Output format, either ``"json"`` or ``"csv"``.
        output: Path to write the CSV/JSON report.
    """

    def __init__(
        self,
        engines: List[EngineConfig],
        judges: List[JudgeConfig] | None = None,
        *,
        tasks: str = ".",
        task: str | None = None,
        max_concurrent: int = 1,
        timeout: float = 60.0,
        format: str = "json",
        output: str | None = None,
    ) -> None:
        if not engines:
            raise ConfigError("configuration must define at least one engine")
        names = [e.name for e in engines]
        if len(set(names)) != len(names):
            raise ConfigError(f"duplicate engine names: {names}")
        self.engines = engines
        self.judges = judges or []
        self.tasks = tasks
        self.task = task
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.format = format
        self.output = output

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkConfig":
        """Build a :class:`BenchmarkConfig` from a mapping."""
        if not isinstance(data, dict):
            raise ConfigError("configuration root must be a mapping")
        engines_data = data.get("engines")
        if not isinstance(engines_data, list):
            raise ConfigError("'engines' must be a list")
        engines = [EngineConfig.from_dict(e) for e in engines_data]
        judges_data = data.get("judges")
        judges = []
        if judges_data:
            if not isinstance(judges_data, list):
                raise ConfigError("'judges' must be a list")
            judges = [JudgeConfig.from_dict(j) for j in judges_data]
        return cls(
            engines=engines,
            judges=judges,
            tasks=data.get("tasks", "."),
            task=data.get("task"),
            max_concurrent=data.get("max_concurrent", 1),
            timeout=data.get("timeout", 60.0),
            format=data.get("format", "json"),
            output=data.get("output"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain mapping."""
        return {
            "engines": [e.to_dict() for e in self.engines],
            "judges": [j.to_dict() for j in self.judges],
            "tasks": self.tasks,
            "task": self.task,
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "format": self.format,
            "output": self.output,
        }

    def __eq__(self, other: object) -> bool:  # noqa: E501
        if not isinstance(other, BenchmarkConfig):
            return NotImplemented
        return (
            self.engines == other.engines
            and self.judges == other.judges
            and self.tasks == other.tasks
            and self.task == other.task
            and self.max_concurrent == other.max_concurrent
            and self.timeout == other.timeout
            and self.format == other.format
            and self.output == other.output
        )

    def __repr__(self) -> str:  # noqa: E501
        return (
            f"BenchmarkConfig(engines={self.engines!r}, judges={self.judges!r}, "
            f"tasks={self.tasks!r}, task={self.task!r}, "
            f"max_concurrent={self.max_concurrent!r}, format={self.format!r})"
        )


# Centralized default values for the benchmark and the UI. These live in one
# place so the CLI, the config file and the web dashboard all agree, instead of
# each hardcoding the same numbers.
DEFAULT_ENGINE_BASE_URL = "http://localhost:11434"
DEFAULT_ENGINE_MODEL = "llama3"
DEFAULT_JUDGE_BASE_URL = "http://localhost:11434"
DEFAULT_JUDGE_MODEL = "llama3"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_CONCURRENT = 1
DEFAULT_FORMAT = "json"
DEFAULT_TASKS = "."
DEFAULT_OUTPUT = "results.json"
DEFAULT_TRIALS = 3


class Defaults:
    """Default values for the engine, judge and benchmark parameters.

    Used by the CLI, config-file construction and the web dashboard so the
    three surfaces share a single source of truth.
    """

    engine_base_url: str = DEFAULT_ENGINE_BASE_URL
    engine_model: str = DEFAULT_ENGINE_MODEL
    judge_base_url: str = DEFAULT_JUDGE_BASE_URL
    judge_model: str = DEFAULT_JUDGE_MODEL
    timeout: float = DEFAULT_TIMEOUT
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    format: str = DEFAULT_FORMAT
    tasks: str = DEFAULT_TASKS
    task: str | None = None
    output: str = DEFAULT_OUTPUT
    trials: int = DEFAULT_TRIALS
    engines: List[EngineConfig] = []

    def to_dict(self) -> Dict[str, Any]:
        """Return the defaults as a plain mapping."""
        return {
            "engine_base_url": self.engine_base_url,
            "engine_model": self.engine_model,
            "judge_base_url": self.judge_base_url,
            "judge_model": self.judge_model,
            "timeout": self.timeout,
            "max_concurrent": self.max_concurrent,
            "format": self.format,
            "tasks": self.tasks,
            "task": self.task,
            "output": self.output,
            "trials": self.trials,
            "engines": [e.to_dict() for e in self.engines],
        }

    def select_engine(self, name: str) -> EngineConfig | None:
        """Return the configured engine identified by *name*.

        *name* matches :attr:`EngineConfig.name` (the value sent by the
        dashboard's engine dropdown). Returns ``None`` if no engine matches.
        """
        for engine in self.engines:
            if engine.name == name:
                return engine
        return None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Defaults):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:  # noqa: E501
        return f"Defaults({self.to_dict()})"


def default_engine() -> EngineConfig:
    """Return a new :class:`EngineConfig` populated with the default values."""
    return EngineConfig(
        name="default",
        base_url=DEFAULT_ENGINE_BASE_URL,
        model=DEFAULT_ENGINE_MODEL,
        timeout=DEFAULT_TIMEOUT,
        max_concurrent=DEFAULT_MAX_CONCURRENT,
    )


def default_judge() -> JudgeConfig:
    """Return a new :class:`JudgeConfig` populated with the default values."""
    return JudgeConfig(
        name="default",
        base_url=DEFAULT_JUDGE_BASE_URL,
        model=DEFAULT_JUDGE_MODEL,
        timeout=DEFAULT_TIMEOUT,
    )


def _is_absolute_http_url(url: str) -> bool:
    """Return ``True`` if *url* is an absolute ``http`` or ``https`` URL."""
    return url.strip().startswith(("http://", "https://"))


def _sniff_format(path: Path) -> str:
    """Return ``"json"`` or ``"yaml"`` based on the file extension."""
    if path.suffix == ".json":
        return "json"
    return "yaml"


def _load_yaml(data: str) -> Dict[str, Any]:
    """Parse a YAML document into a mapping, raising :class:`ConfigError`."""
    try:
        parsed = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ConfigError("invalid YAML") from exc
    if not isinstance(parsed, dict):
        raise ConfigError("configuration root must be a mapping")
    return parsed


def _load_json(data: str) -> Dict[str, Any]:
    """Parse a JSON document into a mapping, raising :class:`ConfigError`."""
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ConfigError("invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ConfigError("configuration root must be a mapping")
    return parsed


def load_config(path: str | os.PathLike[str]) -> BenchmarkConfig:
    """Load a benchmark configuration from *path*.

    The format is sniffed from the file extension (``.json`` → JSON, otherwise
    YAML). JSON is a subset of YAML, so a JSON file is also valid YAML.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"configuration file not found: {path}")
    format_ = _sniff_format(path)
    with path.open("r", encoding="utf-8") as handle:
        raw = handle.read()
    parser = _load_json if format_ == "json" else _load_yaml
    data = parser(raw)
    return BenchmarkConfig.from_dict(data)


def write_config(config: BenchmarkConfig, path: str | os.PathLike[str]) -> None:
    """Write a benchmark configuration to *path* (JSON when the path ends in ``.json``)."""
    path = Path(path)
    if path.suffix == ".json":
        payload = json.dumps(config.to_dict(), indent=2)
    else:
        payload = yaml.safe_dump(config.to_dict(), sort_keys=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(payload)
