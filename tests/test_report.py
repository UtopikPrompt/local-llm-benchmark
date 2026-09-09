"""Tests for the result row and report serialization.

Covers :class:`Row`, :data:`CSV_COLUMNS`, :func:`write_csv`,
:func:`write_json`, :func:`write_report`, and :func:`print_summary`.
"""

import csv
import io

import pytest

from local_llm_benchmark.report import print_summary, write_csv, write_json, write_report
from local_llm_benchmark.results import CSV_COLUMNS, Row


def _rows():
    return [
        Row(
            engine="engine-a",
            model="m1",
            judge="judge",
            task_id="qa-1",
            category="qa",
            prompt="p1",
            expected="2007",
            output="answer",
            ttft_s=0.5,
            tok_per_s=100.0,
            iters_per_s=3.0,
            quality_passed=True,
            quality_deterministic=True,
            quality_judge=True,
            quality_note="ok",
        ),
        Row(
            engine="engine-a",
            model="m2",
            task_id="qa-2",
            category="math",
            prompt="p2",
            quality_passed=False,
            quality_note="fail",
        ),
    ]


def test_row_to_dict():
    row = Row(
        engine="e", model="m", judge="j", task_id="t", category="qa",
        prompt="p", expected="x", output="o",
        ttft_s=0.1, tok_per_s=1.0, iters_per_s=2.0,
        quality_passed=True, quality_deterministic=True, quality_judge=True, quality_note="n",
    )
    assert row.to_dict() == {
        "engine": "e",
        "model": "m",
        "judge": "j",
        "task_id": "t",
        "category": "qa",
        "prompt": "p",
        "expected": "x",
        "output": "o",
        "ttft_s": 0.1,
        "tok_per_s": 1.0,
        "iters_per_s": 2.0,
        "quality_passed": True,
        "quality_deterministic": True,
        "quality_judge": True,
        "quality_note": "n",
    }


def test_csv_columns_include_judge():
    assert "judge" in CSV_COLUMNS
    assert CSV_COLUMNS == tuple(CSV_COLUMNS)


def test_write_csv(tmp_path):
    path = tmp_path / "report.csv"
    write_csv(_rows(), path)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert len(rows) == 2
    assert [r["engine"] for r in rows] == ["engine-a", "engine-a"]
    # The judge column is written for the first row.
    assert rows[0]["judge"] == "judge"
    # Quality booleans are written as text.
    assert rows[0]["quality_passed"] == "True"


def test_write_json(tmp_path):
    path = tmp_path / "report.json"
    write_json(_rows(), path)
    data = path.read_text()
    assert path.endswith(".json")
    assert '"judge"' in data
    assert '"quality_passed"' in data


def test_write_report_dispatches_by_format(tmp_path):
    # JSON format writes JSON.
    json_path = tmp_path / "r.json"
    write_report(_rows(), json_path, fmt="json")
    assert json_path.read_text().startswith("[")

    # CSV format writes CSV with the header row.
    csv_path = tmp_path / "r.csv"
    write_report(_rows(), csv_path, fmt="csv")
    assert csv_path.read_text().startswith("engine,model,")


def test_print_summary_empty():
    # Should not raise; prints a friendly message.
    print_summary([])


def test_print_summary_aggregates(tmp_path, capsys):
    rows = _rows()
    print_summary(rows)
    out = capsys.readouterr().out
    assert "engine-a" in out
    assert "rows:         2" in out
    assert "quality_passed:   1/2" in out
    assert "deterministic:    1/2" in out


def test_print_summary_lists_judges(tmp_path, capsys):
    rows = [Row(engine="e", model="m", judge="gpt", task_id="t", category="qa")]
    print_summary(rows)
    assert "judges:       gpt" in capsys.readouterr().out
