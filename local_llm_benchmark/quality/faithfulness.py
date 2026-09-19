"""Faithfulness metric.

Per ADR-016 this is a judge-only dimension: faithfulness is best assessed by an
LLM-as-judge rather than an exact-match signal.

Pure standard library. The judge call is supplied by the caller via ``judge``.
"""

from __future__ import annotations

import re
from typing import Callable


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens, dropping punctuation."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def faithfulness_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    source: str = "",
) -> float:
    """LLM-as-judge score for how faithful an answer is to its source.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param source: the source/context the answer should be faithful to.
    :return: faithfulness score in ``[0.0, 1.0]`` (1.0 == fully faithful).
    """
    return judge_score(answer, judge, source)


def judge_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    source: str = "",
) -> float:
    """Extract the 0..1 faithfulness score from a judge response.

    :param answer: the judge's response text.
    :param judge: unused, retained for interface symmetry.
    :param source: unused, retained for interface symmetry.
    :return: faithfulness score parsed from ``answer`` in ``[0.0, 1.0]``.
    """
    tokens = _tokenize(answer)
    if not tokens:
        return 0.0

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

    return judge("Rate how faithful this answer is to its source on a scale of 0 to 1.", {})


def faithfulness_metrics(
    answer: str,
    judge: Callable[[str, dict], dict],
    source: str = "",
) -> dict:
    """Compute the full faithfulness metric set.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param source: the source/context the answer should be faithful to.
    :return: dict with ``judge`` and the ``faithfulness`` score.
    """
    judge_result = judge(
        f"Rate how faithful this answer is to its source on a scale of 0 to 1.\n\nSource: {source}\n\nAnswer:\n{answer}",
        {},
    )
    return {
        "judge": judge_result["score"],
        "faithfulness": judge_score(
            judge_result.get("raw", answer), judge, source
        ),
    }
