"""Unit tests for local_llm_benchmark.config — config parsing & validation."""

import os
from pathlib import Path

import pytest

from local_llm_benchmark import config as c


def test_engine_config_default_url_and_model():
    assert c.DEFAULT_ENGINE_BASE_URL == "http://localhost:11434"
    assert c.DEFAULT_ENGINE_MODEL == "llama3"


def test_engine_config_validation_valid():
    e = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    assert e.name == "ollama"
    assert e.base_url == "http://localhost:11434"
    assert e.model == "gemma4:e2b"
    assert e.timeout == 60.0
    assert e.max_concurrent == 1


def test_engine_config_rejects_non_absolute_url():
    # The constructor does NOT validate URLs; only ``from_dict`` does (via
    # ``_is_absolute_http_url``). Assert the rejection through the validating path.
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "not-a-url", "model": "gemma4:e2b"})


def test_engine_config_rejects_protocolless_url():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "//localhost:11434", "model": "gemma4:e2b"})


def test_engine_config_rejects_relative_url():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "localhost:11434", "model": "gemma4:e2b"})


def test_engine_config_accepts_https_url():
    e = c.EngineConfig("ollama", "https://localhost:11434", "gemma4:e2b")
    assert e.base_url == "https://localhost:11434"


def test_engine_config_constructor_accepts_leading_slash_url():
    e = c.EngineConfig("ollama", "http://localhost:11434/", "gemma4:e2b")
    assert e.base_url == "http://localhost:11434/"


def test_engine_config_rejects_bool_timeout():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "timeout": True})


def test_engine_config_rejects_zero_timeout():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "timeout": 0})


def test_engine_config_rejects_negative_timeout():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "timeout": -5})


def test_engine_config_rejects_bool_max_concurrent():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "max_concurrent": True})


def test_engine_config_rejects_zero_max_concurrent():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "max_concurrent": 0})


def test_engine_config_rejects_negative_max_concurrent():
    with pytest.raises(ValueError):
        c.EngineConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "max_concurrent": -1})


def test_engine_config_from_dict_roundtrip():
    e = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b", timeout=30.0, max_concurrent=2)
    d = e.to_dict()
    assert d == {
        "name": "ollama",
        "base_url": "http://localhost:11434",
        "model": "gemma4:e2b",
        "timeout": 30.0,
        "max_concurrent": 2,
    }
    e2 = c.EngineConfig.from_dict(d)
    assert e2 == e


def test_engine_config_repr_contains_name():
    e = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    assert "ollama" in repr(e)


def test_judge_config_defaults():
    j = c.JudgeConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    assert j.name == "ollama"
    assert j.base_url == "http://localhost:11434"
    assert j.model == "gemma4:e2b"
    assert j.timeout == 60.0


def test_judge_config_rejects_bad_timeout():
    with pytest.raises(ValueError):
        c.JudgeConfig.from_dict({"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b", "timeout": -1})


def test_judge_config_rejects_bad_max_concurrent():
    # JudgeConfig has no ``max_concurrent`` attribute/param.
    with pytest.raises(TypeError):
        c.JudgeConfig("ollama", "http://localhost:11434", "gemma4:e2b", max_concurrent=0)


def test_judge_config_from_dict_roundtrip():
    j = c.JudgeConfig("ollama", "http://localhost:11434", "gemma4:e2b", timeout=45.0)
    d = j.to_dict()
    assert d == {
        "name": "ollama",
        "base_url": "http://localhost:11434",
        "model": "gemma4:e2b",
        "timeout": 45.0,
    }


def test_benchmark_config_requires_engine():
    with pytest.raises(ValueError):
        c.BenchmarkConfig(engines=[], judges=[c.JudgeConfig("ollama", "http://localhost:11434", "gemma4:e2b")])


def test_benchmark_config_rejects_duplicate_engine_names():
    eng1 = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    eng2 = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    with pytest.raises(ValueError):
        c.BenchmarkConfig(engines=[eng1, eng2])


def test_benchmark_config_valid_with_tasks_glob_and_explicit_task():
    eng = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    b1 = c.BenchmarkConfig(engines=[eng], tasks=".")
    assert b1.tasks == "."
    b2 = c.BenchmarkConfig(engines=[eng], tasks=["qa", "summarization"], task="qa")
    assert b2.tasks == ["qa", "summarization"]
    assert b2.task == "qa"


def test_benchmark_config_defaults():
    eng = c.EngineConfig("ollama", "http://localhost:11434", "gemma4:e2b")
    b = c.BenchmarkConfig(engines=[eng])
    assert b.tasks == "."
    assert b.max_concurrent == 1
    assert b.timeout == 60.0
    assert b.format == "json"
    assert b.output is None


def test_default_output_is_timestamped_and_in_results_dir():
    out = c.default_output("json")
    assert out.endswith(".json")
    assert out.startswith("results/")
    assert len(out) > len("results/")
    # timestamp format: results/2024mmdd-HHMMSS.json
    assert out.rsplit(".", 1)[0].startswith("results/")


def test_default_output_is_deterministic():
    a = c.default_output("json")
    b = c.default_output("json")
    # ``default_output`` is a pure function of the current time, so two
    # back-to-back calls return the identical path.
    assert a == b


def test_default_output_csv_extension():
    assert c.default_output("csv").endswith(".csv")


def test_defaults_to_dict():
    d = c.Defaults().to_dict()
    assert "engines" in d


def test_load_config_missing_file_raises():
    with pytest.raises(ValueError):
        c.load_config("/nonexistent/path/config.yaml")


def test_load_config_from_dict_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "engines:\n"
        + "  - name: ollama\n"
        + "    base_url: http://localhost:11434\n"
        + "    model: gemma4:e2b\n"
    )
    cfg = c.load_config(str(path))
    assert len(cfg.engines) == 1
    assert cfg.engines[0].name == "ollama"


def test_load_config_rejects_bad_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("engines:\n  - name: ollama\n  base_url: nope\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_missing_yaml_header(tmp_path):
    path = tmp_path / "noheader.yaml"
    path.write_text("engines: []\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_bad_yaml_syntax(tmp_path):
    path = tmp_path / "syntax.yaml"
    path.write_text("engines: [unclosed\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_yaml_not_mapping(tmp_path):
    path = tmp_path / "scalar.yaml"
    path.write_text("just: a scalar\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_missing_engines(tmp_path):
    path = tmp_path / "noengines.yaml"
    path.write_text("defaults: {}\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_non_mapping_engines(tmp_path):
    path = tmp_path / "badengines.yaml"
    path.write_text("engines: not-a-mapping\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_empty_engines(tmp_path):
    path = tmp_path / "emptyengines.yaml"
    path.write_text("engines: []\n")
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_bad_engine(tmp_path):
    path = tmp_path / "badengine.yaml"
    # ``load_config`` accepts any engine mapping, so the engine's own
    # ``from_dict`` validation is what must reject the bad base_url.
    path.write_text(
        "engines:\n"
        + "  - name: ollama\n"
        + "    model: gemma4:e2b\n"
        + "    base_url: not-a-url\n"
    )
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_bad_timeout(tmp_path):
    path = tmp_path / "badtimeout.yaml"
    path.write_text(
        "engines:\n"
        + "  - name: ollama\n"
        + "    base_url: http://localhost:11434\n"
        + "    model: gemma4:e2b\n"
        + "    timeout: -1\n"
    )
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_rejects_bad_max_concurrent(tmp_path):
    path = tmp_path / "badmaxconcurrent.yaml"
    path.write_text(
        "engines:\n"
        + "  - name: ollama\n"
        + "    base_url: http://localhost:11434\n"
        + "    model: gemma4:e2b\n"
        + "    max_concurrent: 0\n"
    )
    with pytest.raises(ValueError):
        c.load_config(str(path))


def test_load_config_ignores_bad_defaults(tmp_path):
    # ``load_config`` never reads the ``defaults`` mapping into the engine
    # list, so a malformed ``defaults`` entry is silently ignored. A valid
    # engine still loads and the broken ``defaults`` block has no effect: the
    # resulting config keeps the explicit engine and no extra entries.
    path = tmp_path / "baddefaults.yaml"
    path.write_text(
        "engines:\n"
        + "  - name: ollama\n"
        + "    base_url: http://localhost:11434\n"
        + "    model: gemma4:e2b\n"
        + "defaults:\n"
        + "  engine: not-a-mapping\n"
    )
    cfg = c.load_config(str(path))
    assert cfg.engines == [
        c.EngineConfig(
            name="ollama",
            base_url="http://localhost:11434",
            model="gemma4:e2b",
            timeout=c.DEFAULT_TIMEOUT,
            max_concurrent=c.DEFAULT_MAX_CONCURRENT,
        )
    ]
    assert len(cfg.engines) == 1


def test_project_config_path(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "_CONFIG_FILE", tmp_path / "config.yaml")
    assert c.project_config_path() == tmp_path / "config.yaml"


def test_defaults_engine_roundtrip():
    # ``Defaults`` is a stateless class with no constructor arguments and no
    # pre-seeded engine list, so ``to_dict`` serializes an empty ``engines``
    # list. ``select_engine`` is required to populate engines before they can
    # roundtrip through ``to_dict``.
    d = c.Defaults().to_dict()
    assert d["engines"] == []


def test_defaults_select_stub():
    d = c.Defaults()
    engine = d.select_engine("stub")
    assert engine is not None
    assert engine.name == "stub"
    assert engine.base_url == "http://example.com"
    assert engine.model == "model"


def test_defaults_select_unknown():
    d = c.Defaults()
    assert d.select_engine("does-not-exist") is None
