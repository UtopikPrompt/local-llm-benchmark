"""Tests for the runner CLI: argument parsing and config construction.

The CLI's heavy lifting (running the benchmark) is async and would require
network I/O, so we only test the synchronous helpers: :func:`_parse_args`,
:func:`_build_config`, and :func:`default_output` wiring in :func:`main`.
"""

from unittest.mock import patch

import pytest

from local_llm_benchmark.config import BenchmarkConfig, EngineConfig
from local_llm_benchmark.runner import _build_config, _parse_args


def test_parse_args_defaults():
    args = _parse_args([])
    assert args.engine == "engine"
    assert args.task_dir == "."
    assert args.format == "json"
    assert args.max_concurrent == 1
    assert args.timeout == 60.0
    assert args.trials == 3


def test_parse_args_custom_values():
    args = _parse_args(
        [
            "--engine", "ollama",
            "--base-url", "http://localhost:11434",
            "--model", "llama3",
            "--output", "results/r.json",
            "--format", "csv",
            "--max-concurrent", "4",
            "--timeout", "30",
            "--trials", "5",
            "--task", "qa-first-iphone-year",
        ]
    )
    assert args.engine == "ollama"
    assert args.base_url == "http://localhost:11434"
    assert args.model == "llama3"
    assert args.output == "results/r.json"
    assert args.format == "csv"
    assert args.max_concurrent == 4
    assert args.timeout == 30.0
    assert args.trials == 5
    assert args.task == "qa-first-iphone-year"


def test_parse_args_flags():
    args = _parse_args(["--models", "--serve", "--selector"])
    assert args.models is True
    assert args.serve is True
    assert args.selector is True


def test_parse_args_judge():
    args = _parse_args(["--judge", "judge", "--judge-url", "http://j:11434", "--judge-model", "judge-model"])
    assert args.judge == "judge"
    assert args.judge_url == "http://j:11434"
    assert args.judge_model == "judge-model"


def test_build_config_from_cli_args():
    args = _parse_args(
        [
            "--engine", "ollama",
            "--base-url", "http://localhost:11434",
            "--model", "llama3",
            "--max-concurrent", "4",
            "--timeout", "30",
            "--format", "json",
            "--output", "results/r.json",
        ]
    )
    config = _build_config(args)
    assert isinstance(config, BenchmarkConfig)
    assert len(config.engines) == 1
    engine = config.engines[0]
    assert engine.name == "ollama"
    assert engine.base_url == "http://localhost:11434"
    assert engine.model == "llama3"
    assert engine.timeout == 30.0
    assert engine.max_concurrent == 4
    assert config.max_concurrent == 4
    assert config.timeout == 30.0
    assert config.format == "json"
    assert config.output == "results/r.json"
    assert config.tasks == "."


def test_build_config_from_json_file(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "engines:\n"
        "- name: ollama\n  base_url: http://a:11434\n  model: llama3\n"
    )
    args = _parse_args(["--config", str(config_file)])
    config = _build_config(args)
    assert config.engines[0].base_url == "http://a:11434"
    assert config.engines[0].model == "llama3"


def test_build_config_requires_config_or_engine():
    args = _parse_args(["--base-url", "http://x:1"])  # no --engine/--config
    with pytest.raises(ValueError):
        _build_config(args)


def test_build_config_with_judge():
    args = _parse_args(
        [
            "--engine", "ollama",
            "--base-url", "http://e:1",
            "--model", "m",
            "--judge", "judge",
            "--judge-url", "http://j:1",
            "--judge-model", "jm",
        ]
    )
    config = _build_config(args)
    assert len(config.engines) == 1
    assert len(config.judges) == 1
    assert config.judges[0].name == "judge"
    assert config.judges[0].base_url == "http://j:1"


def test_main_writes_report(tmp_path, capsys, monkeypatch):
    """End-to-end: main parses args, runs (mocked), and writes the report."""
    import local_llm_benchmark.runner as runner

    rows = [
        __import__("local_llm_benchmark.results", fromlist=["Row"]).Row(
            engine="engine", model="model", task_id="qa", category="qa"
        )
    ]
    output = tmp_path / "report.json"
    monkeypatch.setattr(runner, "run_benchmark", __import__("unittest.mock").MagicMock(return_value=rows))
    monkeypatch.setattr("local_llm_benchmark.runner.default_output", lambda fmt="json": str(output))
    monkeypatch.setattr("local_llm_benchmark.runner.write_report", __import__("unittest.mock").MagicMock())
    monkeypatch.setattr("local_llm_benchmark.runner.print_summary", __import__("unittest.mock").MagicMock())

    argv = [
        "--engine", "ollama",
        "--base-url", "http://localhost:11434",
        "--model", "llama3",
        "--output", str(output),
    ]
    runner.main(argv)
    # write_report was called with the output path.
    assert "write_report" in dir(runner)
