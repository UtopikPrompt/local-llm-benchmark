"""Quality module.

Implements the three quality dimensions defined in ADR-004/005:

- :mod:`local_llm_benchmark.quality.accuracy` — static accuracy (EM + F1).
- :mod:`local_llm_benchmark.quality.groundedness` — premise-faithfulness.
- :mod:`local_llm_benchmark.quality.judge` — LLM-as-judge pairwise comparison.

Weighting, dimension qualification, and aggregation are intentionally *deferred*
(no ideal) per ADR-020: any subset of dimensions may be enabled for a benchmark,
and the per-dimension/per-benchmark weighting is re-evaluated as needed. There
is no single prescribed hybrid scoring formula.
"""

from __future__ import annotations

from local_llm_benchmark.quality.accuracy import (
    exact_match,
    exact_match_score,
    f1_score,
    accuracy_metrics,
)
from local_llm_benchmark.quality.groundedness import (
    topical_similarity,
    find_best_support,
    groundedness_score,
    groundedness_metrics,
)
from local_llm_benchmark.quality.judge import (
    PairwiseResult,
    pairwise_ranking,
    judge_pair,
    make_judge,
    DEFAULT_PROMPT,
)
from local_llm_benchmark.quality.reasoning import (
    internal_consistency,
    structural_complexity,
    reasoning_score,
    reasoning_metrics,
)
from local_llm_benchmark.quality.instruction_following import (
    instruction_following_score,
    instruction_following_metrics,
)
from local_llm_benchmark.quality.relevance import (
    topic_overlap,
    relevance_score,
    relevance_metrics,
)
from local_llm_benchmark.quality.harmfulness import (
    safety_keywords,
    harmfulness_score,
    harmfulness_metrics,
)
from local_llm_benchmark.quality.faithfulness import (
    faithfulness_score,
    faithfulness_metrics,
)
from local_llm_benchmark.quality.metrics import (
    Dimension,
    DIMENSIONS,
    Aggregator,
)

__all__ = [
    # accuracy
    "exact_match",
    "exact_match_score",
    "f1_score",
    "accuracy_metrics",
    # groundedness
    "topical_similarity",
    "find_best_support",
    "groundedness_score",
    "groundedness_metrics",
    # judge
    "PairwiseResult",
    "pairwise_ranking",
    "judge_pair",
    "make_judge",
    "DEFAULT_PROMPT",
    # reasoning
    "internal_consistency",
    "structural_complexity",
    "reasoning_score",
    "reasoning_metrics",
    # instruction following
    "instruction_following_score",
    "instruction_following_metrics",
    # relevance
    "topic_overlap",
    "relevance_score",
    "relevance_metrics",
    # harmfulness
    "safety_keywords",
    "harmfulness_score",
    "harmfulness_metrics",
    # faithfulness
    "faithfulness_score",
    "faithfulness_metrics",
    # registry / aggregator
    "Dimension",
    "DIMENSIONS",
    "Aggregator",
]
