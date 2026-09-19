"""Groundedness metric: premise-faithfulness of an answer to source material.

Adopts the groundedness dimension of ADR-004: how faithfully an answer reflects
its retrieved source passages. Computes a sentence-level faithfulness score and
the fraction of unsupported sentences. Pure standard library.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

import math

_SENTENCE_RE = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens, dropping punctuation."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def _sentence_tokenize(text: str) -> list[str]:
    """Split text into sentence tokens (used for faithfulness)."""
    return [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]


def _vector(text: str) -> Counter:
    """Word-frequency vector for a block of text."""
    return Counter(_tokenize(text))


def topical_similarity(claim: str, premise: str) -> float:
    """Cosine similarity between a claim and a premise.

    Uses word-frequency vectors with L2 normalization. Returns a similarity in
    ``[0.0, 1.0]``.

    :param claim: a sentence or short claim from the answer.
    :param premise: a source passage to compare against.
    :return: cosine similarity in ``[0.0, 1.0]``.
    """
    claim_vec = _vector(claim)
    premise_vec = _vector(premise)
    if not claim_vec or not premise_vec:
        return 0.0

    # Dot product of the two vectors.
    dot = sum((claim_vec & premise_vec).total())
    if dot == 0.0:
        return 0.0

    claim_norm = math.sqrt(sum(c * c for c in claim_vec.values()))
    premise_norm = math.sqrt(sum(p * p for p in premise_vec.values()))
    if premise_norm == 0.0:
        return 0.0
    return dot / (claim_norm * premise_norm)


def _combined_vector(premises: Iterable[str]) -> Counter:
    """Merge all premises into a single pooled word-frequency vector."""
    combined: Counter = Counter()
    for premise in premises:
        combined.update(_vector(premise))
    return combined


def find_best_support(claim: str, premises: Iterable[str]) -> tuple[float, str]:
    """Return the (similarity, premise) of the most-supporting passage.

    :param claim: a claim from the answer.
    :param premises: the source passages.
    :return: ``(max_similarity, best_premise)``.
    """
    best_similarity = 0.0
    best_premise = ""
    for premise in premises:
        similarity = topical_similarity(claim, premise)
        if similarity > best_similarity:
            best_similarity = similarity
            best_premise = premise
    return best_similarity, best_premise


def groundedness_score(answer: str, premises: Iterable[str]) -> float:
    """Premise-faithfulness score for an answer.

    For each sentence in the answer, the claim is supported if its best-matching
    premise has a topical similarity above a threshold. The score is the fraction
    of sentences supported.

    :param answer: the model's answer.
    :param premises: the source passages the answer should be grounded in.
    :return: fraction of sentences supported (0.0 to 1.0).
    """
    answer_sentences = _sentence_tokenize(answer)
    if not answer_sentences or not premises:
        return 0.0

    threshold = 0.3
    supported = 0
    for sentence in answer_sentences:
        _, best_premise = find_best_support(sentence, premises)
        if topical_similarity(sentence, best_premise) >= threshold:
            supported += 1
    return supported / len(answer_sentences)


def groundedness_metrics(answer: str, premises: Iterable[str]) -> dict:
    """Compute the groundedness metric set for an answer.

    :param answer: the model's answer.
    :param premises: the source passages the answer should be grounded in.
    :return: dict with ``groundedness`` (faithfulness) and
        ``unsupported_sentences`` counts.
    """
    answer_sentences = _sentence_tokenize(answer)
    if not answer_sentences or not premises:
        return {
            "groundedness": 0.0,
            "unsupported_sentences": len(answer_sentences) if answer_sentences else 0,
        }

    threshold = 0.3
    unsupported = 0
    for sentence in answer_sentences:
        _, best_premise = find_best_support(sentence, premises)
        if topical_similarity(sentence, best_premise) < threshold:
            unsupported += 1
    return {
        "groundedness": groundedness_score(answer, premises),
        "unsupported_sentences": unsupported,
    }
