"""Relevance metric.

Per ADR-016 this is a judge-only dimension: relevance is best assessed by an
LLM-as-judge rather than an exact-match signal.

Pure standard library. The judge call is supplied by the caller via ``judge``.
"""

from __future__ import annotations

import re
from typing import Callable


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens, dropping punctuation."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def topic_overlap(answer: str, topic: str) -> float:
    """A Jaccard-style overlap between the tokens of an answer and a topic.

    Provides a static proxy for relevance so the judge has a numeric anchor.

    :param answer: the model's answer.
    :param topic: the topic the answer should address.
    :return: token overlap in ``[0.0, 1.0]``.
    """
    answer_tokens = set(_tokenize(answer))
    topic_tokens = set(_tokenize(topic))
    if not answer_tokens or not topic_tokens:
        return 0.0
    return len(answer_tokens & topic_tokens) / len(answer_tokens | topic_tokens)


def relevance_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    topic: str = "",
) -> float:
    """LLM-as-judge score for how relevant an answer is to a topic.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param topic: the topic the answer should address.
    :return: relevance score in ``[0.0, 1.0]``.
    """
    return judge_score(answer, judge, topic)


def judge_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    topic: str = "",
) -> float:
    """Extract the 0..1 relevance score from a judge response.

    :param answer: the judge's response text.
    :param judge: unused, retained for interface symmetry.
    :param topic: unused, retained for interface symmetry.
    :return: relevance score parsed from ``answer`` in ``[0.0, 1.0]``.
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

    return judge("Rate relevance on a scale of 0 to 1.", {})


def relevance_metrics(
    answer: str,
    judge: Callable[[str, dict], dict],
    topic: str = "",
) -> dict:
    """Compute the full relevance metric set.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param topic: the topic the answer should address.
    :return: dict with ``overlap`` and the ``relevance`` score.
    """
    overlap = topic_overlap(answer, topic)
    judge_result = judge(
        f"Rate how relevant this answer is to the topic on a scale of 0 to 1.\n\nTopic: {topic}\n\nAnswer:\n{answer}",
        {},
    )
    return {
        "overlap": overlap,
        "judge": judge_result["score"],
        "relevance": judge_score(
            judge_result.get("raw", answer), judge, topic
        ),
    }
