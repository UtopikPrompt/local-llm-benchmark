"""Unit tests for local_llm_benchmark.results — Row serialization."""

import csv
import io

import pytest

from local_llm_benchmark import report, results as r


def test_row_to_dict_fields():
    row = r.Row(
        engine="ollama",
        model="gemma4:e2b",
        judge="ollama",
        task_id="qa",
        category="qa",
        prompt="What is 2+2?",
        expected="4",
        output="4",
        ttft_s=0.1,
        tok_per_s=10.0,
        iters_per_s=100.0,
        quality_passed=True,
        quality_deterministic=True,
        quality_judge=True,
        quality_note="",
    )
    d = row.to_dict()
    assert d["engine"] == "ollama"
    assert d["model"] == "gemma4:e2b"
    assert d["judge"] == "ollama"
    assert d["task_id"] == "qa"
    assert d["category"] == "qa"
    assert d["prompt"] == "What is 2+2?"
    assert d["expected"] == "4"
    assert d["output"] == "4"
    assert d["ttft_s"] == 0.1
    assert d["tok_per_s"] == 10.0
    assert d["iters_per_s"] == 100.0
    assert d["quality_passed"] is True
    assert d["quality_deterministic"] is True
    assert d["quality_judge"] is True
    assert d["quality_note"] == ""


def test_row_to_dict_defaults():
    row = r.Row(engine="", model="")
    d = row.to_dict()
    assert d["judge"] == ""
    assert d["task_id"] == ""
    assert d["category"] == "qa"
    assert d["ttft_s"] == 0.0
    assert d["tok_per_s"] == 0.0
    assert d["iters_per_s"] == 0.0
    assert d["quality_passed"] is False
    assert d["quality_deterministic"] is False
    assert d["quality_judge"] is False
    assert d["quality_note"] == ""


def test_csv_columns_count_matches_row_fields():
    assert len(r.CSV_COLUMNS) == 15


def test_csv_columns_order():
    assert list(r.CSV_COLUMNS) == [
        "engine",
        "model",
        "judge",
        "task_id",
        "category",
        "prompt",
        "expected",
        "output",
        "ttft_s",
        "tok_per_s",
        "iters_per_s",
        "quality_passed",
        "quality_deterministic",
        "quality_judge",
        "quality_note",
    ]


def test_write_csv(tmp_path):
    rows = [
        r.Row(
            engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o", ttft_s=0.1
        ),
        r.Row(engine="ollama", model="llama3", prompt="q2", expected="e2", output="o2", ttft_s=0.2),
    ]
    out = tmp_path / "bench.csv"
    report.write_csv(rows, out)
    assert out.exists()
    with out.open() as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        assert fieldnames == list(r.CSV_COLUMNS)
        data = list(reader)
    assert len(data) == 2
    assert data[0]["engine"] == "ollama"
    assert data[0]["model"] == "gemma4:e2b"
    assert data[0]["ttft_s"] == "0.1"
    assert data[1]["model"] == "llama3"


def test_write_csv_header_only(tmp_path):
    rows = []
    out = tmp_path / "empty.csv"
    report.write_csv(rows, out)
    assert out.exists()
    with out.open() as f:
        reader = csv.reader(f)
        rows_list = list(reader)
    assert rows_list == [list(r.CSV_COLUMNS)]


def test_write_json(tmp_path):
    rows = [
        r.Row(
            engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o", ttft_s=0.1
        ),
    ]
    out = tmp_path / "bench.json"
    report.write_json(rows, out)
    assert out.exists()
    import json

    with out.open() as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert data[0]["engine"] == "ollama"
    assert data[0]["ttft_s"] == 0.1


def test_write_report_json(tmp_path):
    rows = [
        r.Row(
            engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o", ttft_s=0.1
        ),
    ]
    out = tmp_path / "bench.json"
    report.write_report(rows, out)
    assert out.exists()
    import json

    with out.open() as f:
        data = json.load(f)
    assert data[0]["engine"] == "ollama"


def test_write_report_csv(tmp_path):
    rows = [
        r.Row(
            engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o", ttft_s=0.1
        ),
    ]
    out = tmp_path / "bench.csv"
    report.write_report(rows, out, fmt="csv")
    assert out.exists()
    with out.open() as f:
        reader = csv.DictReader(f)
        assert list(reader.fieldnames) == list(r.CSV_COLUMNS)
        assert len(list(reader)) == 1


def test_write_report_dispatch(tmp_path):
    rows = [r.Row(engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o")]
    json_out = tmp_path / "j.json"
    csv_out = tmp_path / "c.csv"
    report.write_report(rows, json_out, fmt="json")
    report.write_report(rows, csv_out, fmt="csv")
    import json

    assert json_out.exists()
    assert csv_out.exists()
    assert json_out.read_text().strip() != ""
    assert csv_out.read_text().strip() != ""


def test_write_report_default_format_json(tmp_path):
    rows = [r.Row(engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o")]
    out = tmp_path / "bench.json"
    report.write_report(rows, out)
    import json

    data = json.loads(out.read_text())
    assert data[0]["engine"] == "ollama"


def test_write_report_creates_parent_dir(tmp_path):
    rows = [r.Row(engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o")]
    out = tmp_path / "nested" / "dir" / "bench.json"
    report.write_report(rows, out)
    assert out.exists()


def test_write_csv_in_memory(tmp_path):
    rows = [r.Row(engine="ollama", model="gemma4:e2b", prompt="q", expected="e", output="o")]
    out = tmp_path / "bench.csv"
    report.write_csv(rows, out)
    with out.open() as f:
        reader = csv.DictReader(f)
        assert list(reader.fieldnames) == list(r.CSV_COLUMNS)
        assert len(list(reader)) == 1
