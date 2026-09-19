---
name: Quality comparison via LLM-as-judge
type: decision
status: accepted
date: 2026-09-19
summary: Compare open-ended quality using an LLM-as-judge with structured-output scoring.
---

# ADR-005: Quality comparison — LLM-as-judge

## Context

ADR-004 covers accuracy and groundedness, which answer closed, measurable questions. For open-ended
quality ("which answer is better, more helpful, or safer?") the project requested a comparison
method, and chose an **LLM-as-judge** approach.

## Decision

Compare open-ended quality using an **LLM-as-judge**: a reference model scores candidate outputs
from different models/engines via structured-output requests (e.g., dimensions like helpfulness,
correctness, faithfulness, safety) using the OpenAI-compatible API (ADR-003).

## Consequences

- **Flexible, model-agnostic scoring.** The judge can evaluate any open-ended dimension without a
  fixed dataset.
- **Reuses the engine interface.** The judge model runs through the same OpenAI-compatible client,
  so it can be any model (e.g., the models under test, or a stronger reference model).
- **Structured outputs.** Deterministic, parseable scores enable aggregation and comparison.
- **Judge variance.** LLM judges are not perfectly reliable; scores should be averaged over multiple
  prompts and/or use pairwise comparisons to reduce variance.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. LLM-as-judge | LLM scores outputs via structured output | Flexible, captures nuance, reuses engine API | Judge variance, extra cost |
| B. Static datasets only | Fixed-answer benchmarks | Deterministic, cheap | Can't measure open-ended quality |
| C. Human evaluation | LLM/humans grade outputs | Ground truth | Expensive, slow, non-scalable |
| D. Embedding similarity | Semantic similarity to references | Fast, cheap | No nuance, no correctness |

Option A best matches the request for open-ended quality comparison while reusing the engine
interface and avoiding human-labeling costs. Option B can't measure open-ended quality; Option C is
costly and slow; Option D lacks nuance and correctness signal.

## Open points

- Use pairwise comparison to reduce judge variance (ADR-009).
- How many judge prompts / samples to average over for statistical significance. No preference
  expressed; deferred for future optimization (ADR-009).
- Which judge model to standardize on (a stronger reference vs. one of the models under test).
  Set by the user at runtime.
