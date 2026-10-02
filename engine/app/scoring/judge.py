"""LLM-as-judge scoring pipeline (§5).

The judge pipeline scores benchmarked model outputs using a *dedicated*,
configurable judge LLM. Per :doc:`§decision 4 <../decisions>` the judge model is
deliberately **not** one of the engines being benchmarked, so it cannot be
biased by grading its own output. It uses the same OpenAI-compatible interface
as the benchmarked engines (the ``openai`` SDK), so it can target any compatible
endpoint configured via ``JUDGE_API_KEY`` / ``JUDGE_API_BASE`` /
``JUDGE_MODEL`` environment variables.

The rubric is fixed: a 1-5 scale over factual correctness, instruction
adherence and constraint satisfaction. Per-challenge model/rubric overrides are
supported via :class:`Judge.overrides` (§decision 5).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from openai import OpenAI


class RubricCategory(str, Enum):
    """Fixed rubric dimensions (§5)."""

    FACTUAL_CORRECTNESS = "factual_correctness"
    INSTRUCTION_ADHERENCE = "instruction_adherence"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"


@dataclass(frozen=True)
class RubricCriterion:
    name: RubricCategory
    description: str


_DEFAULT_RUBRIC: tuple[RubricCriterion, ...] = (
    RubricCriterion(
        RubricCategory.FACTUAL_CORRECTNESS,
        (
            "factual_correctness: Does the output faithfully reflect the facts "
            "present in the source? Award high scores for accurate, well-"
            "sourced content and penalize hallucinations or claims that "
            "contradict the source."
        ),
    ),
    RubricCriterion(
        RubricCategory.INSTRUCTION_ADHERENCE,
        (
            "instruction_adherence: Does the output follow the requested "
            "instructions and output format? Award high scores for faithful "
            "adherence and penalize omitted or altered instructions."
        ),
    ),
    RubricCriterion(
        RubricCategory.CONSTRAINT_SATISFACTION,
        (
            "constraint_satisfaction: Are all hard constraints satisfied "
            "(length limits, schema, required fields, negative constraints, "
            "etc.)? Award high scores for full compliance and penalize any "
            "violated constraint."
        ),
    ),
)


@dataclass(frozen=True)
class Rubric:
    """The fixed 1-5 rubric."""

    criteria: tuple[RubricCriterion, ...] = _DEFAULT_RUBRIC

    def formatted(self) -> str:
        lines = ["Rate each dimension on a 1-5 scale (1 = poor, 5 = excellent)."]
        lines += [f"- {c.name.value}: {c.description}" for c in self.criteria]
        return "\n".join(lines)


@dataclass
class JudgeRequest:
    challenge_id: str
    instruction: str
    source: str
    output: str
    rubric: Rubric = field(default_factory=Rubric)


@dataclass
class JudgeResponse:
    score: int
    reasoning: str
    criterion_scores: Dict[str, int] = field(default_factory=dict)

    def validate(self) -> None:
        """Ensure the score is an integer in the fixed 1-5 rubric range."""
        if not isinstance(self.score, int) or not 1 <= self.score <= 5:
            raise ValueError(
                f"judge score must be an integer in [1, 5]; got {self.score!r}"
            )


# --------------------------------------------------------------------------- #
# Response parsing
# --------------------------------------------------------------------------- #
def _extract_json_block(content: str) -> str:
    """Pull a JSON object out of a (possibly fenced or chatty) model reply."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
    content = re.sub(r"```$", "", content).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        return content[start : end + 1]
    return content


def _extract_score(content: str) -> int:
    for token in re.findall(r"\d+", content):
        value = int(token)
        if 1 <= value <= 5:
            return value
    raise ValueError(f"could not find a 1-5 score in: {content!r}")


def parse_judge_response(content: str) -> JudgeResponse:
    """Parse a raw judge reply into a :class:`JudgeResponse`.

    Accepts either a JSON object (``{"score", "reasoning", "criterion_scores"}``)
    or a bare integer 1-5.
    """
    data: Dict[str, Any]
    try:
        data = json.loads(_extract_json_block(content))
    except (json.JSONDecodeError, ValueError):
        data = {"score": _extract_score(content), "reasoning": content.strip()}

    criterion_scores = {
        str(k): int(v) for k, v in data.get("criterion_scores", {}).items()
    }

    return JudgeResponse(
        score=int(data["score"]),
        reasoning=str(data.get("reasoning", "")),
        criterion_scores=criterion_scores,
    )


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #
def build_judge_prompt(request: JudgeRequest) -> str:
    return (
        "You are an impartial judge evaluating a model output against the "
        "source text it was derived from and the instructions that were given.\n\n"
        f"{request.rubric.formatted()}\n\n"
        "=== SOURCE ===\n"
        f"{request.source}\n\n"
        "=== INSTRUCTIONS ===\n"
        f"{request.instruction}\n\n"
        "=== OUTPUT TO SCORE ===\n"
        f"{request.output}\n\n"
        "Respond with a JSON object containing:\n"
        "- \"score\": an integer 1-5 representing the overall score\n"
        "- \"reasoning\": a brief explanation of your score\n"
        "Optional: \"criterion_scores\": an object mapping each dimension\n"
        "name to a 1-5 integer. Respond with nothing but the JSON object.\n"
    )


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class JudgeConfig:
    """Configuration for the dedicated judge model.

    The ``model`` defaults to a standalone model that is not one of the
    engines under test (§decision 4); it can be overridden per challenge.
    """

    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.0
    rubric: Rubric = field(default_factory=Rubric)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> JudgeConfig:
        env = os.environ if env is None else env
        return cls(
            model=env.get("JUDGE_MODEL", "gpt-4o-mini"),
            api_key=env.get("JUDGE_API_KEY"),
            api_base=env.get("JUDGE_API_BASE"),
            temperature=float(env.get("JUDGE_TEMPERATURE", "0.0")),
            rubric=Rubric(),
        )


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class JudgeClient:
    """Wraps the OpenAI-compatible interface used to query the judge model."""

    def __init__(
        self,
        config: JudgeConfig | None = None,
        client: Any | None = None,
    ) -> None:
        self.config = config or JudgeConfig.from_env()
        if client is None:
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            client = OpenAI(api_key=api_key, base_url=self.config.api_base)
        self._client = client

    def score(self, request: JudgeRequest) -> JudgeResponse:
        messages = [
            {
                "role": "system",
                "content": "You are an objective judge. Respond only with JSON.",
            },
            {"role": "user", "content": build_judge_prompt(request)},
        ]
        completion = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=max(0.0, self.config.temperature),
        )
        content = completion.choices[0].message.content
        return parse_judge_response(content)


# --------------------------------------------------------------------------- #
# Orchestrator with per-challenge overrides (§decision 5)
# --------------------------------------------------------------------------- #
class Judge:
    def __init__(
        self,
        config: JudgeConfig | None = None,
        client: JudgeClient | None = None,
        overrides: Mapping[str, JudgeConfig] | None = None,
    ) -> None:
        self._client = client or JudgeClient(config)
        self._overrides = dict(overrides or {})

    @property
    def config(self) -> JudgeConfig:
        return self._client.config

    @property
    def overrides(self) -> Dict[str, JudgeConfig]:
        return dict(self._overrides)

    def score(
        self,
        challenge_id: str,
        *,
        instruction: str,
        source: str,
        output: str,
    ) -> JudgeResponse:
        """Score a single challenge output, applying any override if present."""
        config = self._overrides.get(challenge_id) or self._client.config
        request = JudgeRequest(
            challenge_id=challenge_id,
            instruction=instruction,
            source=source,
            output=output,
            rubric=config.rubric,
        )
        return self._client.score(request)