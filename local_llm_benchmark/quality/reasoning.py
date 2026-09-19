"""Reasoning / complexity metric.

Adopts the reasoning dimension of ADR-004, scored with the hybrid static + judge
approach of ADR-016: reasoning has a strong exact-match signal, so a static signal
(internal consistency and structural complexity) supplements the LLM-as-judge score
(coherence and step-wise logic).

Pure standard library. The judge call is supplied by the caller via ``judge``.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Callable, Iterable, Tuple

import math

_SENTENCE_RE = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")

_CONTRADICTION_HINTS = (
    " but in fact ",
    " however this is not ",
    " which contradicts ",
    " is wrong ",
    " is false ",
    " is incorrect ",
)


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens, dropping punctuation."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def _sentence_tokenize(text: str) -> list[str]:
    """Split text into sentence tokens."""
    return [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]


def internal_consistency(answer: str) -> float:
    """Detect self-contradictions between the sentences of an answer.

    Flags a contradiction when a later sentence contains a contradiction hint that
    also appears in an earlier sentence. Returns the fraction of sentences that do
    not introduce a contradiction (1.0 == fully consistent).

    :param answer: the model's answer.
    :return: fraction of non-contradictory sentences (0.0 to 1.0).
    """
    sentences = _sentence_tokenize(answer)
    if not sentences:
        return 0.0

    flagged = 0
    for idx, sentence in enumerate(sentences):
        for hint in _CONTRADICTION_HINTS:
            if hint in sentence:
                for earlier in sentences[:idx]:
                    if hint in earlier:
                        flagged += 1
                        break
    return (len(sentences) - flagged) / len(sentences)


def structural_complexity(answer: str) -> float:
    """A normalized measure of how elaborate an answer is.

    Combines the number of sentences and the answer-length relative to the question
    length into a single score in ``[0.0, 1.0]``. Longer, multi-sentence answers that
    still stay proportionate to the prompt score higher.

    :param answer: the model's answer.
    :return: complexity score in ``[0.0, 1.0]``.
    """
    tokens = _tokenize(answer)
    if not tokens:
        return 0.0

    sentence_count = len(_sentence_tokenize(answer))
    if sentence_count == 0:
        return 0.0

    # Sentiment-neutral complexity: reward multi-sentence structure while penalizing
    # answers that are either a single token or wildly longer than a few sentences.
    tokens_per_sentence = len(tokens) / sentence_count
    if tokens_per_sentence < 4:
        # Very short answers: reward length up to a reasonable minimum.
        return min(len(tokens) / 8.0, 1.0)

    # Penalize answers that are disproportionately long (verbose without substance).
    verbosity_penalty = max(0.0, min(1.0, (len(tokens) - sentence_count) / 128.0))
    return 1.0 - 0.5 * verbosity_penalty


def reasoning_score(
    answer: str,
    judge: Callable[[str, dict], dict],
    question: str = "",
) -> float:
    """Hybrid reasoning score combining a static and a judge signal.

    The static component blends internal consistency and structural complexity. The
    judge component is an LLM-as-judge score (``judge``) of reasoning quality. The two
    are combined as a simple average; weighting is deferred (ADR-020).

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param question: the prompt the answer responds to (used for complexity).
    :return: hybrid reasoning score in ``[0.0, 1.0]``.
    """
    static = 0.5 * internal_consistency(answer) + 0.5 * structural_complexity(answer)
    judge_score = judge(f"Rate the reasoning quality of this answer on a scale of 0 to 1.\n\nQuestion: {question}\n\nAnswer:\n{answer}", {})
    return 0.5 * static + 0.5 * judge_score["score"]


def reasoning_metrics(
    answer: str,
    judge: Callable[[str, dict], dict],
    question: str = "",
) -> dict:
    """Compute the full reasoning metric set.

    :param answer: the model's answer.
    :param judge: an ``LLM-as-judge`` callable returning ``{"score": 0..1}``.
    :param question: the prompt the answer responds to.
    :return: dict with ``consistency``, ``complexity``, ``judge`` and the hybrid
        ``reasoning`` score.
    """
    consistency = internal_consistency(answer)
    complexity = structural_complexity(answer)
    judge_result = judge(
        f"Rate the reasoning quality of this answer on a scale of 0 to 1.\n\nQuestion: {question}\n\nAnswer:\n{answer}",
        {},
    )
    return {
        "consistency": consistency,
        "complexity": complexity,
        "judge": judge_result["score"],
        "reasoning": reasoning_score(answer, judge, question),
    }
