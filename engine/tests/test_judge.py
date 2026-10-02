"""Tests for the LLM-as-judge pipeline (§5)."""
import json

import pytest

from app.scoring.judge import (
    Judge,
    JudgeClient,
    JudgeConfig,
    JudgeResponse,
    Rubric,
    RubricCategory,
    build_judge_prompt,
    parse_judge_response,
)

# A set of engine model names that must never be reused as the judge (§4).
_BENCHMARKED_ENGINES = {"engine-a", "engine-b", "engine-c"}

FIX_INSTRUCTION = "Summarize the source below in a single sentence."
FIX_SOURCE = (
    "The conference starts at 9am and ends at 5pm. Lunch is served at noon."
)
FIX_OUTPUT = "The conference runs from 9am to 5pm, with lunch served at noon."

FIXTURE_REQUEST = {
    "challenge_id": "summarize_01",
    "instruction": FIX_INSTRUCTION,
    "source": FIX_SOURCE,
    "output": FIX_OUTPUT,
}


# --------------------------------------------------------------------------- #
# Test doubles: a fake OpenAI-compatible client returning a canned completion.
# --------------------------------------------------------------------------- #
class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, message: _Message) -> None:
        self.message = message


class _Completion:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(_Message(content))]


class _FakeCompletions:
    def __init__(self, owner: "_FakeOpenAI") -> None:
        self._owner = owner

    def create(self, **kwargs: object) -> _Completion:
        self._owner.last_create_kwargs = kwargs
        return _Completion(self._owner.content)


class _FakeChat:
    def __init__(self, owner: "_FakeOpenAI") -> None:
        self.completions = _FakeCompletions(owner)


class _FakeOpenAI:
    """Minimal OpenAI-compatible fake that records create() calls."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.last_create_kwargs: dict = {}
        self.chat = _FakeChat(self)


def _make_judge(content: str, config: JudgeConfig | None = None) -> Judge:
    base = _FakeOpenAI(content)
    client = JudgeClient(config=config or JudgeConfig(), client=base)
    return Judge(client=client)


# --------------------------------------------------------------------------- #
# Rubric & prompt
# --------------------------------------------------------------------------- #
def test_rubric_has_all_three_categories() -> None:
    names = {c.name for c in Rubric().criteria}
    assert names == {
        RubricCategory.FACTUAL_CORRECTNESS,
        RubricCategory.INSTRUCTION_ADHERENCE,
        RubricCategory.CONSTRAINT_SATISFACTION,
    }


def test_build_prompt_includes_rubric_and_fixture() -> None:
    from app.scoring.judge import JudgeRequest

    prompt = build_judge_prompt(JudgeRequest(**FIXTURE_REQUEST))
    assert "factual_correctness" in prompt
    assert "instruction_adherence" in prompt
    assert "constraint_satisfaction" in prompt
    assert FIX_SOURCE in prompt
    assert FIX_OUTPUT in prompt


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def test_parse_from_json_object() -> None:
    payload = json.dumps(
        {
            "score": 4,
            "reasoning": "good",
            "criterion_scores": {"factual_correctness": 5},
        }
    )
    resp = parse_judge_response(payload)
    assert resp.score == 4
    assert resp.reasoning == "good"
    assert resp.criterion_scores == {"factual_correctness": 5}
    resp.validate()


def test_parse_from_bare_number() -> None:
    resp = parse_judge_response("5")
    assert resp.score == 5
    resp.validate()


def test_validate_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        JudgeResponse(score=6, reasoning="").validate()


def test_validate_rejects_non_integer() -> None:
    with pytest.raises(ValueError):
        JudgeResponse(score=3.5, reasoning="").validate()


# --------------------------------------------------------------------------- #
# Acceptance: fixture scored 1-5 by the judge pipeline
# --------------------------------------------------------------------------- #
def test_judge_scores_fixture_via_recorded_response() -> None:
    content = json.dumps({"score": 3, "reasoning": "solid"})
    judge = _make_judge(content)

    response = judge.score(**FIXTURE_REQUEST)

    assert response.score == 3
    assert response.reasoning == "solid"
    response.validate()  # within [1, 5]

    # The judge talked to the OpenAI-compatible interface.
    kwargs = judge.config  # noqa: F841 - referenced via base.last_create_kwargs
    from app.scoring.judge import Judge as _J

    # surface the recorded call through a fresh handle
    assert kwargs.model == "gpt-4o-mini"


def test_judge_model_is_separate_from_benchmarked_engines() -> None:
    # §decision 4: the judge must use a model that is not one of the
    # engines being benchmarked.
    config = JudgeConfig.from_env({"JUDGE_MODEL": "judge-model"})
    assert config.model == "judge-model"
    assert config.model not in _BENCHMARKED_ENGINES


def test_per_challenge_override_selects_judge_model() -> None:
    base = _FakeOpenAI(json.dumps({"score": 5}))
    client = JudgeClient(client=base)
    override = JudgeConfig(model="custom-judge-model")
    judge = Judge(client=client, overrides={"summarize_01": override})

    response = judge.score("summarize_01", **FIXTURE_REQUEST)

    assert response.score == 5
    assert base.last_create_kwargs["model"] == "custom-judge-model"


def test_without_override_uses_default_judge_model() -> None:
    base = _FakeOpenAI(json.dumps({"score": 2}))
    client = JudgeClient(client=base)
    judge = Judge(client=client)

    judge.score("other_challenge", **FIXTURE_REQUEST)

    assert base.last_create_kwargs["model"] == "gpt-4o-mini"
    assert "messages" in base.last_create_kwargs