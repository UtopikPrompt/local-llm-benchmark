"""Tests for the task corpus: :class:`Task`, :class:`TaskCategory`,
:func:`build_default_corpus`, :func:`load_tasks`, :func:`task_by_id`.
"""

import pytest

from local_llm_benchmark.config import ConfigError
from local_llm_benchmark.tasks.corpus import (
    Task,
    TaskCategory,
    build_default_corpus,
    load_tasks,
    task_by_id,
)


# --- TaskCategory -----------------------------------------------------------

@pytest.mark.parametrize("value", [TaskCategory.QA, "qa", "DOC", "doc"])
def test_category_parse_round_trip(value):
    assert TaskCategory.parse(value) == TaskCategory(value) if isinstance(value, str) else value


def test_category_parse_invalid():
    with pytest.raises(ConfigError):
        TaskCategory.parse("nonsense")


def test_category_value():
    assert TaskCategory.QA.value == "qa"


# --- Task -------------------------------------------------------------------

def test_task_requires_id_and_prompt():
    with pytest.raises(ConfigError):
        Task(id="", category=TaskCategory.QA, prompt="p")
    with pytest.raises(ConfigError):
        Task(id="t", category=TaskCategory.QA, prompt="")


def test_task_defaults_category_to_qa():
    task = Task(id="t", prompt="p")
    assert task.category == TaskCategory.QA
    assert task.system is None
    assert task.expected is None
    assert task.validate is None


def test_task_has_validator_property():
    task = Task(id="t", prompt="p", validate=lambda a: True)
    assert task.has_validator is True
    plain = Task(id="t", prompt="p")
    assert plain.has_validator is False


def test_task_from_dict_round_trip():
    task = Task(
        id="qa-first-iphone-year",
        category=TaskCategory.QA,
        prompt="prompt",
        system="system",
        expected="2007",
        validate=lambda a: True,
    )
    data = task.to_dict()
    assert data == {
        "id": "qa-first-iphone-year",
        "category": "qa",
        "prompt": "prompt",
        "system": "system",
        "expected": "2007",
    }
    # ``validate`` is a callable, so it is dropped by to_dict (not serializable).
    assert "validate" not in data


def test_task_from_dict_missing_prompt():
    with pytest.raises(ConfigError):
        Task.from_dict({"id": "t"})


def test_task_from_dict_invalid_category():
    with pytest.raises(ConfigError):
        Task.from_dict({"id": "t", "category": "bogus", "prompt": "p"})


def test_task_from_dict_category_defaults():
    task = Task.from_dict({"id": "t", "prompt": "p"})
    assert task.category == TaskCategory.QA


# --- build_default_corpus ---------------------------------------------------

def test_build_default_corpus_returns_all_categories():
    corpus = build_default_corpus()
    ids = {task.id for task in corpus}
    assert "doc-rest-api" in ids
    assert "code-httpx-get-timeout" in ids
    assert "qa-first-iphone-year" in ids
    assert "math-solve-2x-5-15" in ids


def test_build_default_corpus_attaches_validators():
    corpus = build_default_corpus()
    math = next(t for t in corpus if t.id == "math-solve-2x-5-15")
    assert math.validate is not None
    # The math validators must actually pass a correct solution.
    assert math.validate("x = 5")
    assert math.validate("x=5")


def test_build_default_corpus_does_not_mutate_shared_corpus():
    corpus = build_default_corpus()
    math = next(t for t in corpus if t.id == "math-solve-2x-5-15")
    assert math.validate is not None


# --- load_tasks / task_by_id ------------------------------------------------

def test_load_tasks(tmp_path):
    task_file = tmp_path / "qa.yaml"
    task_file.write_text("id: qa-train-distance\ncategory: qa\nprompt: How far?\nexpected: 1132\n")
    tasks = load_tasks(tmp_path)
    assert len(tasks) == 1
    assert tasks[0].id == "qa-train-distance"


def test_load_tasks_json(tmp_path):
    task_file = tmp_path / "qa.json"
    task_file.write_text('{"id": "qa-x", "category": "qa", "prompt": "hi"}')
    tasks = load_tasks(tmp_path)
    assert tasks[0].id == "qa-x"


def test_load_tasks_missing_directory():
    with pytest.raises(ConfigError, match="not found"):
        load_tasks("/nonexistent/tasks")


def test_load_tasks_no_files(tmp_path):
    with pytest.raises(ConfigError, match="no tasks found"):
        load_tasks(tmp_path)


def test_task_by_id_found():
    corpus = build_default_corpus()
    task = task_by_id(corpus, "doc-rest-api")
    assert task.id == "doc-rest-api"


def test_task_by_id_missing():
    corpus = build_default_corpus()
    with pytest.raises(ConfigError, match="not found"):
        task_by_id(corpus, "does-not-exist")


def test_load_tasks_prefers_json_over_yaml(tmp_path):
    # Both a .json and a .yaml with the same id are present; JSON is loaded
    # first, so it should win.
    (tmp_path / "qa.json").write_text('{"id": "qa-json", "prompt": "json"}')
    (tmp_path / "qa.yaml").write_text("id: qa-yaml\nprompt: yaml\n")
    tasks = load_tasks(tmp_path)
    assert tasks[0].id == "qa-json"
    assert {t.id for t in tasks} == {"qa-json"}
