"""Instruction-following metric.

Per ADR-016 this is a judge-only dimension: there is no strong exact-match signal
for whether an answer obeys instructions, so the LLM-as-judge score is used directly.

Pure standard library. The judge call is supplied by the caller via ``judge``.
"""

from __future__ import annotations

import re
from typing import Callable


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens, dropping punctuation."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def instruction_following_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    instruction: str = "",
) -> float:
    """LLM-as-judge score for how well an answer follows the instruction.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param instruction: the instruction the answer attempts to satisfy.
    :return: instruction-following score in ``[0.0, 1.0]``.
    """
    return judge_score(answer, judge, instruction)


def judge_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    instruction: str = "",
) -> float:
    """Extract the 0..1 score from a judge response.

    Tries the common response shapes a judge might return and falls back to the raw
    text score if parsing fails.

    :param answer: the judge's response text.
    :param judge: unused, retained for interface symmetry.
    :param instruction: unused, retained for interface symmetry.
    :return: score parsed from ``answer`` in ``[0.0, 1.0]``.
    """
    tokens = _tokenize(answer)
    if not tokens:
        return 0.0

    # Prefer an explicit numeric score embedded in the judge text.
    numeric = None
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", answer):
        if float(match.group(2)) != 0:
            numeric = float(match.group(1)) / float(match.group(2))
            break
    if numeric is not None:
        return min(1.0, max(0.0, numeric))

    if "yes" in tokens and "no" not in tokens:
        return 1.0
    if "no" in tokens and "yes" not in tokens:
        return 0.0

    return judge("Rate compliance on a scale of 0 to 1.", {})


def instruction_following_metrics(
    answer: str,
    judge: Callable[[str, dict], dict],
    instruction: str = "",
) -> dict:
    """Compute the instruction-following metric set.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param instruction: the instruction the answer attempts to satisfy.
    :return: dict with ``judge`` and the ``instruction_following`` score.
    """
    judge_result = judge(
        f"Rate how well this answer follows the instruction on a scale of 0 to 1.\n\nInstruction: {instruction}\n\nAnswer:\n{answer}",
        {},
    )
    return {
        "judge": judge_result["score"],
        "instruction_following": judge_score(
            judge_result.get("raw", answer), judge, instruction
        ),
    }
