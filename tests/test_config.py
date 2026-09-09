"""Tests for the configuration data classes and file helpers.

Covers :class:`EngineConfig`, :class:`JudgeConfig`, :class:`BenchmarkConfig`,
:class:`Defaults`, plus :func:`load_config`, :func:`write_config`,
:func:`default_output` and :func:`project_config_path`.
"""

import json

import pytest

from local_llm_benchmark.config import (
    BenchmarkConfig,
    ConfigError,
    Defaults,
    EngineConfig,
    JudgeConfig,
    default_engine,
    default_judge,
    default_output,
    load_config,
    project_config_path,
    write_config,
)


# --- EngineConfig -----------------------------------------------------------

def test_engine_config_round_trip():
    engine = EngineConfig(
        name="ollama",
        base_url="http://localhost:11434",
        model="llama3",
        timeout=120.0,
        max_concurrent=4,
    )
    assert EngineConfig.from_dict(engine.to_dict()) == engine
    assert engine.to_dict() == {
        "name": "ollama",
        "base_url": "http://localhost:11434",
        "model": "llama3",
        "timeout": 120.0,
        "max_concurrent": 4,
    }


@pytest.mark.parametrize(
    "missing",
    [
        {"base_url": "http://x:11434", "model": "m"},
        {"name": "e", "model": "m"},
        {"name": "e", "base_url": "http://x:11434"},
        {},
    ],
)
def test_engine_config_requires_fields(missing):
    with pytest.raises(ConfigError):
        EngineConfig.from_dict(missing)


@pytest.mark.parametrize("bad_url", ["ftp://x", "example.com", "http://x:11434/", "x"])
def test_engine_config_requires_absolute_http_url(bad_url):
    with pytest.raises(ConfigError):
        EngineConfig.from_dict({"name": "e", "base_url": bad_url, "model": "m"})


@pytest.mark.parametrize("bad_timeout", [0, -1, "60", True, None, {"a": 1}])
def test_engine_config_rejects_bad_timeout(bad_timeout):
    with pytest.raises(ConfigError):
        EngineConfig.from_dict({"name": "e", "base_url": "http://x:11434", "model": "m", "timeout": bad_timeout})


@pytest.mark.parametrize("bad_max", [0, -1, 1.5, True, "2", None])
def test_engine_config_rejects_bad_max_concurrent(bad_max):
    with pytest.raises(ConfigError):
        EngineConfig.from_dict({"name": "e", "base_url": "http://x:11434", "model": "m", "max_concurrent": bad_max})


def test_engine_config_default_timeout_and_max():
    engine = EngineConfig("e", "http://x:11434", "m")
    assert engine.timeout == 60.0
    assert engine.max_concurrent == 1


def test_engine_config_accepts_https_and_whitespace_url():
    engine = EngineConfig.from_dict({"name": "e", "base_url": "  https://x:11434/", "model": "m"})
    assert engine.base_url == "https://x:11434/"


# --- JudgeConfig ------------------------------------------------------------

def test_judge_config_round_trip():
    judge = JudgeConfig("judge", "http://localhost:11434", "judge-model", timeout=30.0)
    assert JudgeConfig.from_dict(judge.to_dict()) == judge
    assert judge.to_dict() == {
        "name": "judge",
        "base_url": "http://localhost:11434",
        "model": "judge-model",
        "timeout": 30.0,
    }


def test_judge_config_defaults():
    judge = JudgeConfig("j", "http://x:11434", "m")
    assert judge.timeout == 60.0


def test_judge_config_rejects_bad_url():
    with pytest.raises(ConfigError):
        JudgeConfig.from_dict({"name": "j", "base_url": "not-a-url", "model": "m"})


# --- BenchmarkConfig --------------------------------------------------------

def test_benchmark_config_requires_engine():
    with pytest.raises(ConfigError):
        BenchmarkConfig.from_dict({"engines": []})


def test_benchmark_config_rejects_duplicate_engine_names():
    with pytest.raises(ConfigError):
        BenchmarkConfig(
            engines=[
                EngineConfig("a", "http://x:1", "m"),
                EngineConfig("a", "http://x:2", "m"),
            ]
        )


def test_benchmark_config_rejects_non_list_engines():
    with pytest.raises(ConfigError):
        BenchmarkConfig.from_dict({"engines": {"name": "a"}})


def test_benchmark_config_rejects_non_list_judges():
    with pytest.raises(ConfigError):
        BenchmarkConfig.from_dict({"engines": [EngineConfig("a", "http://x:1", "m")], "judges": "j"})


def test_benchmark_config_rejects_invalid_engine_entry():
    with pytest.raises(ConfigError):
        BenchmarkConfig.from_dict({"engines": [{"name": "a"}]})


def test_benchmark_config_round_trip():
    config = BenchmarkConfig(
        engines=[EngineConfig("a", "http://x:1", "m")],
        judges=[JudgeConfig("j", "http://x:2", "jm")],
        tasks=".",
        max_concurrent=2,
        timeout=45.0,
        format="json",
        output="results/r.json",
    )
    assert BenchmarkConfig.from_dict(config.to_dict()) == config


def test_benchmark_config_defaults():
    config = BenchmarkConfig(engines=[EngineConfig("a", "http://x:1", "m")])
    assert config.tasks == "."
    assert config.task is None
    assert config.max_concurrent == 1
    assert config.timeout == 60.0
    assert config.format == "json"
    assert config.output is None


# --- Defaults ---------------------------------------------------------------

def test_defaults_to_dict_keys():
    assert set(Defaults().to_dict()) == {
        "engine_base_url",
        "engine_model",
        "judge_base_url",
        "judge_model",
        "timeout",
        "max_concurrent",
        "format",
        "tasks",
        "task",
        "output",
        "trials",
        "engines",
    }


def test_defaults_select_engine():
    Defaults.engines = [EngineConfig("a", "http://a:1", "m"), EngineConfig("b", "http://b:1", "m")]
    assert Defaults().select_engine("a").base_url == "http://a:1"
    assert Defaults().select_engine("missing") is None


def test_defaults_equality():
    assert Defaults() == Defaults()
    assert Defaults() != Defaults.engines


# --- default_engine / default_judge -----------------------------------------

def test_default_engine_values():
    engine = default_engine()
    assert engine.name == "default"
    assert engine.base_url == "http://localhost:11434"
    assert engine.model == "llama3"


def test_default_judge_values():
    judge = default_judge()
    assert judge.name == "default"
    assert judge.base_url == "http://localhost:11434"


# --- default_output ---------------------------------------------------------

def test_default_output_format():
    path = default_output("json")
    assert path.startswith("results/")
    assert path.endswith(".json")
    import re

    assert re.fullmatch(r"results/\d{8}-\d{6}\.json", path)


def test_default_output_format_csv():
    assert default_output("csv").endswith(".csv")


# --- load_config / write_config ---------------------------------------------

def test_write_and_load_json_round_trip(tmp_path):
    config = BenchmarkConfig(
        engines=[EngineConfig("a", "http://x:1", "m", max_concurrent=2)],
        judges=[JudgeConfig("j", "http://x:2", "jm")],
    )
    path = tmp_path / "config.json"
    write_config(config, path)
    assert path.suffix == ".json"
    # Written as JSON, not YAML.
    assert path.read_text().startswith("{")
    assert load_config(path) == config


def test_write_and_load_yaml_round_trip(tmp_path):
    config = BenchmarkConfig(engines=[EngineConfig("a", "http://x:1", "m")])
    path = tmp_path / "config.yaml"
    write_config(config, path)
    text = path.read_text()
    assert "name: a" in text
    assert load_config(path) == config


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_load_sniffs_json_even_when_valid_yaml(tmp_path):
    # A dict is valid YAML, so the JSON sniff must not raise on a .json file.
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"engines": []}))
    assert load_config(path).engines == []


def test_write_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "config.yaml"
    write_config(BenchmarkConfig(engines=[EngineConfig("a", "http://x:1", "m")]), path)
    assert path.exists()


# --- project_config_path ----------------------------------------------------

def test_project_config_path_under_repo():
    path = project_config_path()
    assert path.name == "config.yaml"
    assert path.exists()
    # config.yaml lives at the repo root, one level above src/.
    assert (path.parent / "src").is_dir()
