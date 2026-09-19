"""LLM-as-judge pairwise comparison for open-ended quality.

Adopts ADR-005 (LLM-as-judge with structured output) and ADR-009 (pairwise
comparison) and ADR-013 (cap pairwise candidates per benchmark). The judge runs
through the engine interface (ADR-003) so any model can serve as judge.

Weighting, dimension qualification, and aggregation are intentionally deferred
(no ideal) per ADR-020 — see :mod:`local_llm_benchmark.quality.__init__`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from local_llm_benchmark.engine import Engine, EngineConfig, EngineError


@dataclass
class PairwiseResult:
    """Outcome of judging a single pair of outputs."""

    a: str
    b: str
    winner: str
    tie: bool = False

    @property
    def a_wins(self) -> bool:
        return not self.tie and self.winner == "a"

    @property
    def b_wins(self) -> bool:
        return not self.tie and self.winner == "b"


# Default judging prompt template. The judge compares two outputs on a dimension
# and replies with "a", "b", or "tie".
DEFAULT_PROMPT = (
    "You are an expert evaluator. Compare two responses to the same task on a "
    "single dimension.\n"
    "Task: {task}\n"
    "Response A: {a}\n"
    "Response B: {b}\n"
    "Which response is better on the dimension? Reply with exactly one of: "
    "a, b, or tie. Do not include any other text."
)


def _build_prompt(
    task: str,
    dimension: str,
    a: str,
    b: str,
    template: str = DEFAULT_PROMPT,
) -> str:
    return template.format(task=task, dimension=dimension, a=a, b=b)


def pairwise_ranking(
    judge: Callable[[str], str],
    outputs: list[str],
    task: str,
    dimension: str = "helpfulness",
    template: str = DEFAULT_PROMPT,
    max_candidates: int = 10,
) -> list[tuple[str, float]]:
    """Rank a list of outputs using pairwise comparisons.

    Performs full pairwise comparison over at most ``max_candidates`` outputs
    (ADR-013), asking the judge which of each pair is better. Each output's
    score is the number of pairwise wins; outputs the judge called a tie in all
    its comparisons receive 0.0. Results are returned sorted descending by win
    count, then by name for determinism (ADR-020: aggregation method deferred).

    :param judge: callable that returns the judge's verdict ("a", "b", "tie")
        for a prompt. Runs through the engine interface (ADR-003).
    :param outputs: the candidate outputs to rank.
    :param task: the task context included in each judge prompt.
    :param dimension: the quality dimension being judged.
    :param template: the judging prompt template.
    :param max_candidates: cap on the number of candidates evaluated pairwise
        (ADR-013).
    :return: list of ``(name, win_count)`` sorted by win count descending.
    """
    outputs = outputs[:max_candidates]
    names = [f"candidate-{i}" for i in range(len(outputs))]

    wins: list[int] = [0] * len(outputs)
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            prompt = _build_prompt(task, dimension, outputs[i], outputs[j], template)
            verdict = judge(prompt)
            if verdict.strip() == "a":
                wins[i] += 1
            elif verdict.strip() == "b":
                wins[j] += 1
            # "tie" grants no win to either side.

    return sorted(
        zip(names, wins),
        key=lambda pair: (-pair[1], pair[0]),
    )


def judge_pair(
    judge: Callable[[str], str],
    a: str,
    b: str,
    task: str,
    dimension: str = "helpfulness",
    template: str = DEFAULT_PROMPT,
) -> PairwiseResult:
    """Judge a single pair of outputs.

    :param judge: callable returning the verdict for a prompt.
    :param a: the first candidate output.
    :param b: the second candidate output.
    :param task: task context for the judge prompt.
    :param dimension: the quality dimension being judged.
    :param template: the judging prompt template.
    :return: :class:`PairwiseResult` describing the outcome.
    """
    prompt = _build_prompt(task, dimension, a, b, template)
    verdict = judge(prompt).strip().lower()
    if verdict in ("a", "1", "first", "x"):
        return PairwiseResult(a=a, b=b, winner="a")
    if verdict in ("b", "2", "second", "y"):
        return PairwiseResult(a=a, b=b, winner="b")
    return PairwiseResult(a=a, b=b, winner="", tie=True)


def make_judge(
    engine: Engine,
    config: EngineConfig,
    model: str,
    temperature: float = 0.0,
    template: str = DEFAULT_PROMPT,
) -> Callable[[str], str]:
    """Create a judge callable backed by an engine instance.

    The judge sends a structured-output request through the engine interface
    (ADR-003) using the provided engine and config. The returned callable takes
    a prompt string and returns the judge's raw text response.

    :param engine: the engine to run the judge on.
    :param config: connection config for the judge engine.
    :param model: the model name to request from the engine.
    :param temperature: sampling temperature (0.0 for deterministic judging).
    :param template: the judging prompt template.
    :return: a callable that returns the judge's verdict text.
    """
    config.model = model

    def _judge(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        completion = engine.chat(
            messages=messages,
            seed=42,
            temperature=temperature,
            max_tokens=16,
        )
        return completion.content

    return _judge
