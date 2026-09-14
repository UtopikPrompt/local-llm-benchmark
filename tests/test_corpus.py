"""Unit tests for local_llm_benchmark.tasks.corpus — task corpus & loading."""

import pytest

from local_llm_benchmark.tasks import corpus
from local_llm_benchmark.tasks.corpus import ConfigError, Task, TaskCategory


def test_task_category_parse_valid():
    assert TaskCategory.parse("qa") == TaskCategory.QA


def test_task_category_parse_valid_qa():
    assert TaskCategory.parse("qa") == TaskCategory.QA
    with pytest.raises(ConfigError):
        TaskCategory.parse("questions_and_answers")


def test_task_category_parse_unknown_raises():
    import pytest

    with pytest.raises(ConfigError):
        TaskCategory.parse("nonexistent")


def test_task_category_parse_invalid():
    with pytest.raises(ConfigError):
        TaskCategory.parse("nonexistent")


def test_task_category_all_have_category():
    assert {v.value for v in TaskCategory} == {"doc", "code", "qa", "math"}


def test_build_default_corpus_count():
    tasks = corpus.build_default_corpus()
    assert len(tasks) == 8


def test_build_default_corpus_ids_unique():
    tasks = corpus.build_default_corpus()
    ids = [task.id for task in tasks]
    assert len(ids) == len(set(ids))


def test_build_default_corpus_all_have_required_fields():
    tasks = corpus.build_default_corpus()
    for task in tasks:
        assert task.id is not None
        assert task.prompt is not None
        assert task.prompt != ""


def test_build_default_corpus_varied_categories():
    tasks = corpus.build_default_corpus()
    categories = {task.category for task in tasks}
    assert len(categories) >= 1


def test_build_default_corpus_has_qa():
    tasks = corpus.build_default_corpus()
    assert any(task.category == TaskCategory.QA for task in tasks)


def test_build_default_corpus_has_qa():
    tasks = corpus.build_default_corpus()
    assert any(task.category == TaskCategory.QA for task in tasks)


def test_build_default_corpus_no_empty_prompts():
    tasks = corpus.build_default_corpus()
    assert all(task.prompt != "" for task in tasks)


def test_build_default_corpus_no_empty_ids():
    tasks = corpus.build_default_corpus()
    assert all(task.id != "" for task in tasks)


def test_build_default_corpus_all_tasks_have_expected():
    tasks = corpus.build_default_corpus()
    for task in tasks:
        assert task.expected is not None


def test_load_tasks_missing_dir_raises():
    with pytest.raises(ConfigError):
        corpus.load_tasks("/nonexistent/tasks/dir")


def test_load_tasks_missing_file_raises():
    with pytest.raises(ConfigError):
        corpus.load_tasks("/nonexistent/tasks/dir/missing.json")


def test_load_tasks_missing_tasks_field_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('{"not": "tasks"}')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_missing_id_field_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"prompt": "q"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_missing_prompt_field_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"id": "t1", "expected": "e1"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_empty_list_raises(tmp_path):
    (tmp_path / "tasks.json").write_text("[]")
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_empty_tasks_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('{"tasks": []}')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_empty_tasks_list_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('{"tasks": []}')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_duplicate_ids_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"id": "dup", "prompt": "a", "expected": "e"}, {"id": "dup", "prompt": "b", "expected": "e2"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_empty_id_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"id": "", "prompt": "a", "expected": "e"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_empty_prompt_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"id": "t1", "prompt": "", "expected": "e"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_non_string_id_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"id": 123, "prompt": "a", "expected": "e"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_unknown_category_raises(tmp_path):
    (tmp_path / "tasks.json").write_text('[{"id": "t1", "category": "weird", "prompt": "a", "expected": "e"}]')
    with pytest.raises(ValueError):
        corpus.load_tasks(str(tmp_path / "tasks.json"))


def test_load_tasks_valid(tmp_path):
    (tmp_path / "mytasks").mkdir()
    (tmp_path / "mytasks" / "qa.json").write_text(
        '{"id": "t1", "category": "qa", "prompt": "What is 2+2?", "expected": "4"}'
    )
    (tmp_path / "mytasks" / "math.json").write_text(
        '{"id": "t2", "category": "math", "prompt": "Summarize this", "expected": "summary"}'
    )
    tasks = corpus.load_tasks(str(tmp_path / "mytasks"))
    assert len(tasks) == 2
    assert {t.id for t in tasks} == {"t1", "t2"}
    qa = tasks[0] if tasks[0].id == "t1" else tasks[1]
    assert qa.id == "t1"
    assert qa.category == TaskCategory.QA
    assert qa.prompt == "What is 2+2?"
    assert qa.expected == "4"


def test_load_tasks_relative_path(tmp_path, monkeypatch):
    (tmp_path / "mytasks").mkdir()
    (tmp_path / "mytasks" / "qa.json").write_text(
        '{"id": "t1", "category": "qa", "prompt": "q", "expected": "e"}'
    )
    monkeypatch.chdir(tmp_path)
    tasks = corpus.load_tasks("mytasks")
    assert len(tasks) == 1
    assert tasks[0].id == "t1"


def test_load_tasks_no_extension(tmp_path):
    (tmp_path / "tasks").write_text(
        '[{"id": "t1", "category": "qa", "prompt": "q", "expected": "e"}]'
    )
    # A file without a .json/.yaml/.yml extension is treated as a directory
    # and contains no task files, so loading raises ConfigError.
    with pytest.raises(ConfigError):
        corpus.load_tasks(str(tmp_path / "tasks"))


def test_task_by_id_missing_raises():
    with pytest.raises(ValueError):
        corpus.task_by_id(corpus.build_default_corpus(), "does-not-exist")


def test_task_by_id_returns_task():
    tasks = corpus.build_default_corpus()
    ids = [task.id for task in tasks]
    # pick a valid id
    target = ids[0]
    assert corpus.task_by_id(tasks, target).id == target


def test_task_by_id_case_sensitive():
    tasks = corpus.build_default_corpus()
    ids = [task.id for task in tasks]
    with pytest.raises(ValueError):
        corpus.task_by_id(tasks, ids[0].upper())
