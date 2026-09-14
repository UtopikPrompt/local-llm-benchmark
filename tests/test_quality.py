"""Unit tests for local_llm_benchmark.eval.quality — quality evaluation."""

from dataclasses import dataclass, field

import pytest

from local_llm_benchmark.config import EngineConfig
from local_llm_benchmark.eval import quality
from local_llm_benchmark.eval.quality import Judge, evaluate_quality
from local_llm_benchmark.engines.base import Engine


class StubEngine(Engine):
    """A stub engine returning deterministic answers for quality evaluation."""

    def __init__(self, answer: str = "yes", *, agree: bool = True):
        self._answer = answer
        self._agree = agree

    async def chat(self, messages, *, max_tokens=64, stream=True):
        yield "yes" if self._agree else "no"

    async def chat_completed(self, messages, *, max_tokens=64):
        return ""

    async def list_models(self, model=None, **kwargs):
        return []

    async def serve(self, engine: EngineConfig) -> None:
        pass

    async def unload_model(self) -> None:
        pass


def make_task(category="qa"):
    from local_llm_benchmark.tasks import corpus
    tasks = corpus.build_default_corpus()
    return tasks[0]


async def test_evaluate_quality_deterministic_pass():
    task = make_task()
    answer = task.expected
    row = await evaluate_quality(task, answer, expected=task.expected, validate=None)
    assert row.quality_passed is True
    assert row.quality_deterministic is True
    assert row.quality_judge is False
    assert row.quality_note == "expected substring found"


async def test_evaluate_quality_deterministic_fail():
    task = make_task()
    answer = "wrong answer"
    row = await evaluate_quality(task, answer, expected=task.expected, validate=None)
    assert row.quality_passed is False
    assert row.quality_deterministic is False
    assert row.quality_judge is False


async def test_evaluate_quality_deterministic_or_judge():
    task = make_task()
    answer = "wrong answer"
    engine = StubEngine(answer="wrong answer")
    judge = Judge(engine=engine, name="judge")
    row = await evaluate_quality(task, answer, expected=task.expected, judge=judge, validate=None)
    assert row.quality_judge is True
    # judge agreed (deterministic failed) so quality_passed should be True
    assert row.quality_passed is True


async def test_evaluate_quality_no_judge():
    task = make_task()
    row = await evaluate_quality(task, task.expected, expected="", validate=None)
    assert row.quality_judge is False
    assert row.quality_passed == row.quality_deterministic


async def test_evaluate_quality_default_expected_empty():
    task = make_task()
    row = await evaluate_quality(task, task.expected, expected="", validate=None)
    assert row.expected == task.expected


async def test_evaluate_quality_default_validate_none():
    task = make_task()
    row = await evaluate_quality(task, task.expected, expected="", validate=None)
    assert row.quality_judge is False


def test_judge_dataclass():
    engine = StubEngine()
    judge = Judge(engine=engine, name="my-judge")
    assert judge.engine is engine
    assert judge.name == "my-judge"


def test_judge_repr():
    engine = StubEngine()
    judge = Judge(engine=engine, name="my-judge")
    assert "my-judge" in repr(judge)


async def test_score_deterministic_agreement():
    task = make_task()
    engine = StubEngine(answer=task.expected)
    judge = Judge(engine=engine, name="judge")
    agreed, note = await judge.score(task, task.expected)
    assert agreed is True


async def test_score_deterministic_disagreement():
    task = make_task()
    engine = StubEngine(answer="different", agree=False)
    judge = Judge(engine=engine, name="judge")
    agreed, note = await judge.score(task, task.expected)
    assert agreed is False


async def test_score_note_not_empty():
    task = make_task()
    engine = StubEngine(answer="different")
    judge = Judge(engine=engine, name="judge")
    agreed, note = await judge.score(task, task.expected)
    assert note != ""


async def test_evaluate_quality_returns_row():
    task = make_task()
    row = await evaluate_quality(task, task.expected, expected="", validate=None)
    assert isinstance(row, quality.Row)
    assert row.task_id == task.id
    assert row.prompt == task.prompt
    assert row.category == task.category.value
