---
name: Quality metrics
type: decision
status: accepted
date: 2026-09-19
summary: Adopt accuracy and groundedness as the quality metrics for the benchmark.
---

# ADR-004: Quality metrics — accuracy and groundedness

## Context

ADR-001 defined the quality pillar but not the concrete metrics. Two complementary dimensions were
requested:

- **Accuracy** — how correct an answer is (task-level correctness).
- **Groundedness** — how faithfully an answer reflects its source material (a RAG/verification
  concern).

## Decision

Adopt **accuracy** and **groundedness** as the two quality metrics:

- **Accuracy**: exact-match (EM) and F1 on static-answer benchmarks (e.g., MMLU, GSM8K, SQuAD-style
  QA).
- **Groundedness**: groundedness / premise-faithfulness scores (e.g., RAGAS groundedness, GEA)
  measuring how well RAG answers are supported by their retrieved sources.

## Consequences

- **Static, reproducible baselines.** Accuracy on static datasets is deterministic and comparable
  across models and engines without extra model calls.
- **RAG coverage.** Groundedness captures a dimension accuracy alone misses — faithfulness to
  sources — which matters for retrieval-augmented use cases.
- **Judging still needed for open-ended quality.** Accuracy/groundedness cover closed, measurable
  questions; open-ended quality comparisons are handled separately by the judge (ADR-005).

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Accuracy + Groundedness | Two complementary dimensions | Covers correctness and RAG faithfulness | Groundedness needs source material |
| B. Accuracy only | Static answer correctness | Simple, fully static | Misses RAG/faithfulness entirely |
| C. RAGAS only | Dedicated RAG evaluation library | Comprehensive RAG metrics | Narrower than the requested scope |
| D. Human evaluation only | LLM/human graders | Captures nuance | Expensive, non-deterministic |

Option A directly satisfies the requested "accuracy and groundedness" scope while keeping the two
dimensions complementary. Option B ignores groundedness; Option C is narrower than requested; Option
D is non-deterministic and costly.

## Open points

- Which static datasets to adopt for accuracy (MMLU, GSM8K, SQuAD, HumanEval, etc.). No preference
  expressed; any widely-used public dataset may be adopted (ADR-008).
- Which groundedness benchmark to adopt (GEA, RAGAS groundedness, etc.). No preference expressed;
  any widely-used public dataset may be adopted (ADR-008).
- Add a third dimension for a complete benchmark (ADR-008). The specific dimension is still open.
