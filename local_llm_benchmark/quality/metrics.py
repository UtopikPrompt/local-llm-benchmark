"""Quality dimension registry and aggregator.

Aggregates the seven quality dimensions defined in ADR-004/005:

- ``accuracy`` — EM + F1 (static).
- ``groundedness`` — premise-faithfulness (static + judge).
- ``reasoning`` — hybrid static + judge.
- ``instruction_following`` — judge-only.
- ``relevance`` — judge-only.
- ``harmfulness`` — judge-only.
- ``faithfulness`` — judge-only.

Weighting and aggregation are intentionally deferred (ADR-020): this module only
records which dimensions exist, their category (static / judge / hybrid), and their
metadata. Any subset may be enabled for a benchmark, and the per-dimension weighting
is re-evaluated as needed — there is no prescribed overall score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from local_llm_benchmark.quality.accuracy import accuracy_metrics
from local_llm_benchmark.quality.groundedness import groundedness_metrics
from local_llm_benchmark.quality.harmfulness import harmfulness_metrics
from local_llm_benchmark.quality.instruction_following import instruction_following_metrics
from local_llm_benchmark.quality.faithfulness import faithfulness_metrics
from local_llm_benchmark.quality.reasoning import reasoning_metrics


@dataclass(frozen=True)
class Dimension:
    """Metadata describing a single quality dimension."""

    name: str
    title: str
    kind: str  # "static" | "judge" | "hybrid"
    requires_judge: bool
    description: str


DIMENSIONS: Tuple[Dimension, ...] = (
    Dimension(
        name="accuracy",
        title="Accuracy",
        kind="static",
        requires_judge=False,
        description="Exact-match accuracy (EM + F1).",
    ),
    Dimension(
        name="groundedness",
        title="Groundedness",
        kind="hybrid",
        requires_judge=True,
        description="Premise-faithfulness (static + judge).",
    ),
    Dimension(
        name="reasoning",
        title="Reasoning / Complexity",
        kind="hybrid",
        requires_judge=True,
        description="Reasoning quality (static + judge).",
    ),
    Dimension(
        name="instruction_following",
        title="Instruction Following",
        kind="judge",
        requires_judge=True,
        description="Instruction-following (judge).",
    ),
    Dimension(
        name="relevance",
        title="Relevance",
        kind="judge",
        requires_judge=True,
        description="Relevance (judge).",
    ),
    Dimension(
        name="harmfulness",
        title="Harmfulness / Safety",
        kind="judge",
        requires_judge=True,
        description="Harmfulness / safety (judge).",
    ),
    Dimension(
        name="faithfulness",
        title="Faithfulness",
        kind="judge",
        requires_judge=True,
        description="Faithfulness (judge).",
    ),
)


@dataclass
class Aggregator:
    """Accumulates per-dimension metrics across a set of responses.

    Aggregation is deliberately permissive (ADR-020): any subset of dimensions may be
    selected, and no overall score is prescribed. The aggregator holds the metrics for
    a single response and can merge a list of responses for comparison.
    """

    dimensions: Tuple[Dimension, ...] = DIMENSIONS
    judges: Dict[str, Callable[[str, dict], dict]] = field(default_factory=dict)
    # Primary score recorded per dimension for each response, keyed by dimension
    # name (ADR-020: aggregation records values only; weighting is deferred).
    scores: Dict[str, List[float]] = field(default_factory=dict)

    def add(
        self,
        answer: str,
        question: str = "",
        instruction: str = "",
        source: str = "",
        context: str = "",
        topic: str = "",
    ) -> dict:
        """Compute metrics for a single response across the enabled dimensions."""
        result: Dict[str, dict] = {}
        for dimension in self.dimensions:
            if dimension.name == "accuracy":
                metrics = accuracy_metrics(answer)
            elif dimension.name == "groundedness":
                metrics = groundedness_metrics(
                    answer, self.judges["groundedness"], source
                )
            elif dimension.name == "reasoning":
                metrics = reasoning_metrics(
                    answer, self.judges["reasoning"], question
                )
            elif dimension.name == "instruction_following":
                metrics = instruction_following_metrics(
                    answer, self.judges["instruction_following"], instruction
                )
            elif dimension.name == "relevance":
                metrics = relevance_metrics(
                    answer, self.judges["relevance"], topic
                )
            elif dimension.name == "harmfulness":
                metrics = harmfulness_metrics(
                    answer, self.judges["harmfulness"], context
                )
            elif dimension.name == "faithfulness":
                metrics = faithfulness_metrics(
                    answer, self.judges["faithfulness"], source
                )
            else:  # pragma: no cover - defensive against unknown dimension
                raise ValueError(f"Unknown dimension: {dimension.name}")
            result[dimension.name] = metrics
            # Record the representative primary score for this dimension. For
            # accuracy the canonical measure is exact_match (f1 is also available);
            # for every other dimension the primary score is the dimension's own key.
            if dimension.name == "accuracy":
                self.scores["accuracy"].append(metrics["exact_match"])
            else:
                self.scores[dimension.name].append(metrics[dimension.name])
        return result

    def add_many(self, responses: List[dict]) -> Dict[str, List[dict]]:
        """Compute metrics for each response in a list.

        :param responses: list of dicts each with ``answer`` and optional
            ``question`` / ``instruction`` / ``source`` / ``context`` / ``topic``.
        :return: mapping of dimension name to the list of per-response metric dicts.
        """
        results: Dict[str, List[dict]] = {name: [] for name, _ in self.dimensions}
        for response in responses:
            metrics = self.add(
                answer=response["answer"],
                question=response.get("question", ""),
                instruction=response.get("instruction", ""),
                source=response.get("source", ""),
                context=response.get("context", ""),
                topic=response.get("topic", ""),
            )
            for name, values in metrics.items():
                results[name].append(values)
        return results

    def mean(self, dimension: str) -> float:
        """Return the mean score of a dimension across ``add_many`` responses.

        :param dimension: the dimension name.
        :return: mean of that dimension's primary score.
        """
        if not self.scores:
            raise ValueError("No results to aggregate; call add_many first.")
        values = self.scores[dimension]
        if not values:
            return 0.0
        return sum(values) / len(values)
