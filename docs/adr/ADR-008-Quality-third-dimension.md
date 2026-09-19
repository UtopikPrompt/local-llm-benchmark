---
name: Complete benchmark — add a third quality dimension
type: decision
status: accepted
date: 2026-09-19
summary: Add a third quality dimension to make the benchmark complete; the specific dimension is still open.
---

# ADR-008: Quality metrics — add a third dimension

## Context

ADR-004 established accuracy and groundedness as the two quality metrics. To deliver a *complete*
benchmark (the project's stated goal), a third dimension is desired. The user has no preference on
the specific static datasets for accuracy or groundedness (any widely-used public dataset may be
adopted), but explicitly wants a complete benchmark.

## Decision

Adopt a **third quality dimension** so the benchmark covers more than closed, measurable questions.
The specific dimension is left open; candidates to consider are:

- **Reasoning / complexity** — e.g., GSM8K-style math, MMLU-pro, or a reasoning score.
- **Instruction-following** — adherence to formatting/role instructions.
- **Relevance** — how well an answer addresses the prompt.
- **Harmfulness / safety** — refusal or safety behavior (may be gated by policy).
- **Hallucination / faithfulness** — a broader faithfulness signal beyond source-groundedness.

Whichever dimension is chosen, it should complement accuracy and groundedness rather than duplicate
them.

## Consequences

- **Broader coverage.** The benchmark moves beyond static correctness and RAG faithfulness toward
  the "complete benchmark" the project targets.
- **Added complexity.** A third dimension may require additional datasets, judge prompts (ADR-005),
  or reference answers, increasing setup cost.
- **Completeness vs. breadth.** The project aims for completeness; over-extending into many
  dimensions risks scope creep, so the third dimension should be adopted deliberately.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Add a third dimension | Complete benchmark | Broader coverage, matches goal | More datasets/judges to maintain |
| B. Accuracy + Groundedness only | Two dimensions | Simpler, focused | Not a "complete" benchmark |
| C. Many dimensions at once | Full suite immediately | Comprehensive | High setup cost, scope creep |

Option A balances completeness with deliberate scope. Option B is too narrow; Option C risks
scope creep before the core is validated.

## Open points

- Which specific third dimension to adopt (reasoning, instruction-following, relevance,
  harmfulness, or a broader faithfulness signal). Resolved → adopt all candidate dimensions
  (ADR-012).
- Which datasets/prompts to adopt for the third dimension once chosen. Resolved → reuse the same
  datasets/prompts as the other dimensions (ADR-012).
- Whether the third dimension should be measured statically or via LLM-as-judge (ADR-005).
  Resolved → measure via LLM-as-judge (ADR-012).
