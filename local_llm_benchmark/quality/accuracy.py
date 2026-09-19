"""Accuracy metrics: exact-match (EM) and F1 on static-answer benchmarks.

Adopts the accuracy dimension of ADR-004: task-level correctness measured as
exact-match and F1 against static reference answers. Pure standard library,
no third-party dependencies.
"""

from __future__ import annotations

import re
from typing import Iterable


def _tokenize(text: str) -> list[str]:
    """Split text into word tokens for F1 computation.

    Lowercases and splits on non-alphanumeric characters, dropping empty
    tokens.
    """
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def exact_match(prediction: str, reference: str) -> bool:
    """Exact-match indicator between a prediction and reference.

    Compares stripped, lowercased text. Two strings match only if they are
    character-for-character identical after normalization.

    :param prediction: the model's output.
    :param reference: the expected answer.
    :return: ``True`` if the prediction exactly matches the reference.
    """
    return prediction.strip().lower() == reference.strip().lower()


def exact_match_score(
    predictions: Iterable[str], references: Iterable[str]
) -> float:
    """Exact-match score across a set of predictions and references.

    :param predictions: one output per example, in order.
    :param references: the expected answer for each example, in order.
    :return: fraction of examples with an exact match (0.0 to 1.0).
    """
    predictions = list(predictions)
    references = list(references)
    if not predictions:
        return 0.0
    return sum(exact_match(p, r) for p, r in zip(predictions, references)) / len(predictions)


def f1_score(
    predictions: Iterable[str], references: Iterable[str]
) -> float:
    """Micro-F1 score across a set of predictions and references.

    Computes token-level precision and recall (micro-averaged) across all
    examples and returns the harmonic mean. Empty predictions and references
    contribute 0.0 to both, matching the convention used by common evaluation
    tooling.

    :param predictions: one output per example, in order.
    :param references: the expected answer for each example, in order.
    :return: micro-F1 in the range 0.0 to 1.0.
    """
    predictions = list(predictions)
    references = list(references)

    ref_tokens: list[list[str]] = [_tokenize(r) for r in references]
    pred_tokens: list[list[str]] = [_tokenize(p) for p in predictions]

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    for pred, ref in zip(pred_tokens, ref_tokens):
        pred_set = set(pred)
        ref_set = set(ref)
        true_positives += len(pred_set & ref_set)
        false_positives += len(pred_set - ref_set)
        false_negatives += len(ref_set - pred_set)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) else 0.0
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def accuracy_metrics(
    predictions: Iterable[str], references: Iterable[str]
) -> dict:
    """Compute the full accuracy metric set for a benchmark.

    :param predictions: one output per example, in order.
    :param references: the expected answer for each example, in order.
    :return: dict with ``exact_match`` and ``f1`` scores.
    """
    return {
        "exact_match": exact_match_score(predictions, references),
        "f1": f1_score(predictions, references),
    }
