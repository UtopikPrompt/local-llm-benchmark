"""Tests for quality scoring: :func:`evaluate_quality` and :class:`Judge`.

Quality has two layers: deterministic checks (expected substring / validator)
and an optional judge model. An answer passes if any deterministic check
passes *or* the judge agrees.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from local_llm_benchmark.config import BenchmarkConfig, EngineConfig, JudgeConfig
from local_llm_benchmark.eval.quality import Judge, evaluate_quality
from local_llm_benchmark.results import Row
from local_llm_benchmark.tasks.corpus import Task, TaskCategory


def _task(expected="2007", validate=None):
    return Task(id="qa", category=TaskCategory.QA, prompt="prompt", expected=expected, validate=validate)


def _row():
    return Row(engine="engine", model="model", task_id="qa", category="qa", prompt="p", expected="2007")


def test_evaluate_expected_substring_match():
    row = evaluate_quality(_task(expected="2007"), "The first iPhone was in 2007.", expected="2007", validate=None)
    assert row.quality_passed is True
    assert row.quality_deterministic is True
    assert row.quality_judge is False
    assert "expected substring found" in row.quality_note


def test_evaluate_expected_substring_case_insensitive():
    row = evaluate_quality(_task(expected="iPhone"), "iPhone released 2007", expected="iPhone", validate=None)
    assert row.quality_passed is True


def test_evaluate_expected_substring_no_match():
    row = evaluate_quality(_task(expected="2007"), "nothing here", expected="2007", validate=None)
    assert row.quality_passed is False
    assert row.quality_deterministic is False


def test_evaluate_validator_pass():
    row = evaluate_quality(_task(expected="x"), "x = 5", expected="x", validate=lambda a: a.strip() == "x = 5")
    assert row.quality_passed is True
    assert row.quality_deterministic is True
    assert "validator passed" in row.quality_note


def test_evaluate_validator_fail():
    row = evaluate_quality(_task(expected="x"), "nope", expected="x", validate=lambda a: a.strip() == "x = 5")
    assert row.quality_passed is False


def test_evaluate_judge_agrees_overrides_negative():
    """The judge can confirm an answer that no deterministic check matched."""
    task = _task(expected="2007")
    judge = Judge(engine=MagicMock(), name="judge")
    judge.score = MagicMock(return_value=(True, "judge agreed"))
    row = evaluate_quality(task, "whatever", expected="2007", validate=None, judge=judge)
    assert row.quality_passed is True
    assert row.quality_deterministic is False
    assert row.quality_judge is True


def test_evaluate_judge_disagrees_overrides_positive():
    """A failing judge can flip a deterministic pass into a fail."""
    task = _task(expected="2007")
    judge = Judge(engine=MagicMock(), name="judge")
    judge.score = AsyncMock(return_value=(False, "judge said no"))
    row = evaluate_quality(task, "2007", expected="2007", validate=None, judge=judge)
    assert row.quality_passed is False
    assert row.quality_deterministic is True
    assert row.quality_judge is False
    # Note composes both layers: "no deterministic match" then judge reason.
    assert "judge said no" in row.quality_note


def test_evaluate_judge_none_means_no_judge():
    row = evaluate_quality(_task(), "answer", expected=None, validate=None, judge=None)
    assert row.quality_passed is False
    assert row.quality_judge is False


def test_evaluate_builds_messages_with_system_prompt():
    import anyio

    task = Task(
        id="qa",
        category=TaskCategory.QA,
        prompt="prompt",
        system="You are helpful",
        expected="2007",
    )
    judge = Judge(engine=MagicMock(), name="judge")
    judge.engine.chat = AsyncMock()
    anyio.run(judge.score, task, "answer")
    messages = judge.engine.chat.call_args.args[0]
    assert messages[0]["role"] == "system"
    assert "You are helpful" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "prompt" in messages[1]["content"]
    assert "2007" in messages[1]["content"]


# --- Judge with a real engine ----------------------------------------------

def test_judge_score_with_fake_engine(monkeypatch):
    from local_llm_benchmark.runner import run_benchmark

    config = BenchmarkConfig(
        engines=[EngineConfig("engine", "http://engine:1", "model")],
        judges=[JudgeConfig("judge", "http://judge:1", "judge-model", timeout=30.0)],
        tasks=".",
    )

    class FakeEngine:
        instances = []

        def __init__(self, c):
            self.config = c
            self.close = AsyncMock()
            FakeEngine.instances.append(self)

        async def close(self):
            pass

    import local_llm_benchmark.eval.quality as quality_module

    monkeypatch.setattr("local_llm_benchmark.runner.OpenAICompatEngine", FakeEngine)

    async def fake_quality(task, output, *, expected, validate, judge):
        return Row(
            engine="", model="", task_id=task.id, category=task.category.value,
            prompt=task.prompt, expected=task.expected or "", output=output,
            quality_passed=True, quality_deterministic=False, quality_judge=True, quality_note="judge agreed",
        )
    monkeypatch.setattr(quality_module, "evaluate_quality", fake_quality)

    rows = anyio.run(run_benchmark, config)

    assert len(rows) == 1
    # The judge engine was constructed and closed exactly once.
    judge_engines = [e for e in FakeEngine.instances if e.config.name == "judge"]
    assert len(judge_engines) == 1
    assert judge_engines[0].close.await_count == 1
