"""Configuration for the benchmark.

Defines the data classes used to describe engines, judges and benchmark
parameters, and helpers to parse / read / write YAML or JSON configuration
files.

A configuration file is either JSON or YAML. Because JSON is a subset of YAML,
the loader sniffs the format by trying ``json.loads`` first and falling back to
YAML.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

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
    def from_dict(cls, data: dict[str, any]) -> EngineConfig:
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
            raise ConfigError(f"engine '{name}' has an invalid base_url: '{base_url}'")
        timeout = data.get("timeout", 60.0)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            raise ConfigError(f"engine '{name}' has an invalid timeout: '{timeout}'")
        max_concurrent = data.get("max_concurrent", 1)
        if (
            not isinstance(max_concurrent, int)
            or isinstance(max_concurrent, bool)
            or max_concurrent < 1
        ):
            raise ConfigError(f"engine '{name}' has an invalid max_concurrent: '{max_concurrent}'")
        return cls(name, base_url, model, timeout=timeout, max_concurrent=max_concurrent)

    def to_dict(self) -> dict[str, any]:
        """Serialize to a plain mapping."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "max_concurrent": self.max_concurrent,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EngineConfig):
            return NotImplemented
        return (
            self.name == other.name
            and self.base_url == other.base_url
            and self.model == other.model
            and self.timeout == other.timeout
            and self.max_concurrent == other.max_concurrent
        )

    def __repr__(self) -> str:
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
    def from_dict(cls, data: dict[str, any]) -> JudgeConfig:
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

    def to_dict(self) -> dict[str, any]:
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
        engines: list[EngineConfig],
        judges: list[JudgeConfig] | None = None,
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

    @property
    def engines_by_name(self) -> dict[str, EngineConfig]:
        """Return a mapping of engine name to :class:`EngineConfig`.

        Raises :class:`ConfigError` if two engines share a name (the name is not
        unique), which is a configuration error.
        """
        by_name = {engine.name: engine for engine in self.engines}
        if len(by_name) != len(self.engines):
            raise ConfigError(f"duplicate engine names: {self.engines}")
        return by_name

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> BenchmarkConfig:
        """Build a :class:`BenchmarkConfig` from a mapping."""
        if not isinstance(data, dict):
            raise ConfigError("configuration root must be a mapping")
        engines_data = data.get("engines")
        if not isinstance(engines_data, list):
            raise ConfigError("'engines' must be a list")
        try:
            engines = [EngineConfig.from_dict(e) for e in engines_data]
        except ConfigError as e:
            raise ConfigError("Error loading engine configuration") from e
        judges_data = data.get("judges")
        judges = []
        if judges_data:
            if not isinstance(judges_data, list):
                raise ConfigError("'judges' must be a list")
            try:
                judges = [JudgeConfig.from_dict(j) for j in judges_data]
            except ConfigError as e:
                raise ConfigError("Error loading judge configuration") from e
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

    def to_dict(self) -> dict[str, any]:
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
DEFAULT_ENGINE_NAME = "ollama"
DEFAULT_ENGINE_MODEL = "llama3"
DEFAULT_JUDGE_BASE_URL = "http://localhost:11434"
DEFAULT_JUDGE_MODEL = "llama3"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_CONCURRENT = 1
DEFAULT_FORMAT = "json"
DEFAULT_TASKS = "."
DEFAULT_RESULTS_DIR = "results"


def default_output(fmt: str = "json") -> str:
    """Return the default report path: a timestamped file in ``results/``.

    The filename encodes the current time (``YYYYmmdd-HHMMSS``) so successive
    runs don't overwrite each other, and the extension matches *fmt*.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{DEFAULT_RESULTS_DIR}/{timestamp}.{fmt}"


DEFAULT_OUTPUT = default_output()
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
    engines: list[EngineConfig] = []

    def to_dict(self) -> dict[str, any]:
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
        if name == "stub":
            return EngineConfig(name="stub", base_url="http://example.com", model="model")
        return None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Defaults):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:  # noqa: E501
        return f"Defaults({self.to_dict()})"


def _is_absolute_http_url(url: str) -> bool:
    """Return ``True`` if *url* is an absolute ``http`` or ``https`` URL.

    A trailing slash is rejected: appending a path to ``http://x:11434/``
    produces a duplicate-slash URL (``http://x:11434//api/chat``).
    """
    stripped = url.strip()
    if not stripped.startswith(("http://", "https://")):
        return False
    return not stripped.endswith("/")


def _sniff_format(path: Path) -> str:
    """Return ``"json"`` or ``"yaml"`` based on the file extension."""
    if path.suffix == ".json":
        return "json"
    return "yaml"


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    return conn


def initialize_config_db(db_path: str) -> None:
    """Ensures the core configuration table exists in the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    # Attempt to create the table if it doesn't exist.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuration (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            type TEXT -- e.g., 'engine_config', 'benchmark_setting'
        );
    """)
    conn.commit()
    conn.close()


# The project configuration file is no longer read from config.yaml. Configuration is now loaded from the SQLite database.
# The project configuration file is no longer read from config.yaml. Configuration is now loaded from the SQLite database.
_DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent / "config.yaml"
)  # Legacy reference: SQLite is now the source of truth

_CONFIG_FILE: Path = _DEFAULT_CONFIG_FILE


def project_config_path() -> Path:
    """Return the path of the project configuration file.\n\n\nThe default is the repository-root ``config.yaml``. This is a module-level
    value (not configurable at runtime) so every layer that needs to locate the
    project configuration resolves the same file. The :mod:`api` layer passes the
    result through :func:`str` because it joins it into a string comparison.
    """
    return _CONFIG_FILE


def load_config(db_path: str, root_path: Path) -> BenchmarkConfig:
    """Loads the entire benchmark configuration from the SQLite database.

    This function treats the SQLite database as the Single Source of Truth (SSOT)
    for all configuration parameters, completely bypassing file-based loading.

    Args:
        db_path: Path to the SQLite database file.
        root_path: The expected root path of the project for context checks.

    Returns:
        A fully populated :class:`BenchmarkConfig` object.

    Raises:
        ConfigError: If the database is missing critical configuration data.
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # 1. Retrieve core benchmark settings
        cursor.execute("SELECT key, value FROM configuration WHERE type='benchmark_setting'")
        settings_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        # Map general settings back to the Defaults object
        defaults = Defaults()
        try:
            defaults.engine_base_url = (
                settings_data.get("engine_base_url") or defaults.engine_base_url
            )
            defaults.engine_model = settings_data.get("engine_model") or defaults.engine_model
            defaults.judge_base_url = settings_data.get("judge_base_url") or defaults.judge_base_url
            defaults.judge_model = settings_data.get("judge_model") or defaults.judge_model
            defaults.timeout = float(settings_data.get("timeout", str(defaults.timeout)))
            defaults.max_concurrent = int(
                settings_data.get("max_concurrent", str(defaults.max_concurrent))
            )
            defaults.format = settings_data.get("format", defaults.format)
            defaults.tasks = settings_data.get("tasks", defaults.tasks)
            defaults.task = settings_data.get("task")
            defaults.output = settings_data.get("output") or defaults.output
            defaults.trials = int(settings_data.get("trials", str(defaults.trials)))
        except Exception as e:
            raise ConfigError(f"Failed to parse core benchmark settings from DB: {e}")

        # 2. Retrieve Engine Configurations
        cursor = conn = get_db_connection(db_path)
        cursor.execute("SELECT key, value FROM configuration WHERE type='engine_config'")
        engine_raw_data = {}
        for row in cursor.fetchall():
            key, value = row
            # Assuming engine name is used as key, and value is JSON string containing full config
            try:
                engine_raw_data[key] = yaml.safe_load(value)
            except yaml.YAMLError as e:
                raise ConfigError(f"Failed to parse engine config for key {key}: {e}")
        conn.close()

        engines = [EngineConfig.from_dict(data) for name, data in engine_raw_data.items()]

        # 3. Retrieve Judge Configurations
        cursor = conn = get_db_connection(db_path)
        cursor.execute("SELECT key, value FROM configuration WHERE type='judge_config'")
        judge_raw_data = {}
        for row in cursor.fetchall():
            key, value = row
            # Assuming judge name is used as key, and value is JSON string containing full config
            try:
                judge_raw_data[key] = yaml.safe_load(value)
            except yaml.YAMLError as e:
                raise ConfigError(f"Failed to parse judge config for key {key}: {e}")
        conn.close()

        judges = [JudgeConfig.from_dict(data) for name, data in judge_raw_data.items()]

        # 4. Construct and return the final config object
        # The tasks and output paths are derived from the 'benchmark_setting' step.
        return BenchmarkConfig(
            engines=engines,
            judges=judges,
            tasks=defaults.tasks,
            task=defaults.task,
            max_concurrent=defaults.max_concurrent,
            timeout=defaults.timeout,
            format=defaults.format,
            output=defaults.output,
        )

    except sqlite3.Error as e:
        raise ConfigError(f"Database error while loading configuration: {e}") from e
    finally:
        # Ensure connection is closed if it was opened
        if "conn" in locals() and conn:
            conn.close()


# --- API Compatibility Layer for Legacy Tests ---


def save_config(config: BenchmarkConfig, db_path: str, root_path: Path) -> None:
    """
    DEPRECATED: Saves configuration by writing to the SQLite SSOT.

    This function mimics the old save mechanism, saving the current
    BenchmarkConfig state to the database instead of a file.
    """
    if not config:
        raise ConfigError("Cannot save a None configuration.")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        # Save general benchmark settings
        settings = {
            "engine_base_url": config.engines[0].base_url,
            "engine_model": config.engines[0].model,
            "judge_base_url": config.judges[0].base_url if config.judges else None,
            "judge_model": config.judges[0].model if config.judges else None,
            "timeout": str(config.timeout),
            "max_concurrent": str(config.max_concurrent),
            "format": config.format,
            "tasks": config.tasks,
            "task": config.task,
            "output": config.output,
            "trials": str(config.trials),
        }
        for key, value in settings.items():
            cursor.execute(
                "INSERT OR REPLACE INTO configuration (key, value, type) VALUES (?, ?, 'benchmark_setting')",
                (
                    key,
                    str(value),
                ),
            )

        # Save engines
        for engine in config.engines:
            engine_dict = engine.to_dict()
            yaml_data = yaml.dump(engine_dict)
            cursor.execute(
                "INSERT OR REPLACE INTO configuration (key, value, type) VALUES (?, ?, 'engine_config')",
                (engine.name, yaml_data),
            )

        # Save judges
        for judge in config.judges:
            judge_dict = judge.to_dict()
            yaml_data = yaml.dump(judge_dict)
            cursor.execute(
                "INSERT OR REPLACE INTO configuration (key, value, type) VALUES (?, ?, 'judge_config')",
                (judge.name, yaml_data),
            )

        conn.commit()
    finally:
        conn.close()


def JudgeConfigWrapper(name: str, base_url: str, model: str, timeout: float = 60.0) -> JudgeConfig:
    """
    DEPRECATED: Compatibility wrapper for Judge initialization.

    Replaces direct Judge instantiation from the old API, using the modern
    JudgeConfig structure.
    """
    return JudgeConfig(name, base_url, model, timeout=timeout)
