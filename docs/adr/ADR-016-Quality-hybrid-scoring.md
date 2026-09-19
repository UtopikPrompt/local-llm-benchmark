---
name: Quality metrics — hybrid static + judge scoring for reasoning
type: decision
status: accepted
date: 2026-09-19
summary: Dimensions with strong exact-match signals (e.g., reasoning) should use a hybrid static + judge score rather than judge-only; the qualification, weighting, and aggregation are deferred (no ideal) per ADR-020.
---

# ADR-016: Quality metrics — hybrid static + judge scoring

## Context

ADR-012 adopted all candidate dimensions, measured via LLM-as-judge (ADR-005), and noted that
dimensions with a strong exact-match signal (e.g., reasoning on GSM8K-style tasks) *may* supplement
the judge score with the exact-match/F1 metric (ADR-004). One open point concerned whether such
dimensions should use a **hybrid static + judge score** rather than judge-only.

## Decision

**Use a hybrid static + judge score** for dimensions with a strong exact-match signal (e.g.,
reasoning). The exact-match/F1 metric (ADR-004) supplements the LLM-as-judge score for these
dimensions, rather than relying on the judge alone.

- **Judging scope.** Dimensions without a strong exact-match signal (instruction-following,
  relevance, faithfulness) remain judge-only.
- **Safety gating.** No dimension requires policy gating or special handling (e.g., harmfulness/safety
  is not gated by policy).

## Consequences

- **More objective reasoning.** Exact-match/F1 anchors reasoning scores against a fixed scale,
  reducing reliance on the judge's absolute calibration.
- **Complementary signals.** The judge captures qualitative reasoning quality (coherence, strategy)
  that exact-match misses; combining both gives a fuller picture.
- **Higher setup.** Reasoning dimensions now need reference answers for exact-match/F1, in addition
  to judge prompts.
- **Consistency preserved.** Only dimensions with a strong exact-match signal use the hybrid; others
  remain judge-only for methodological consistency.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Hybrid static + judge | Exact-match/F1 supplements judge | Objective anchor, complementary | Needs reference answers |
| B. Judge-only | All dimensions judged | Consistent, no reference answers | Less objective on reasoning |
| C. Static-only | Exact-match for all | Fully objective, cheap | Misses qualitative reasoning |

Option A best captures reasoning quality with objective grounding. Option B lacks calibration;
Option C ignores the qualitative signal the judge provides.

## Open points

- Which dimensions qualify as "strong exact-match signal" and use the hybrid (beyond reasoning). Resolved →
  no ideal / deferred (ADR-020).
- How to weight/aggregate the static and judge scores for hybrid dimensions. Resolved → no ideal /
  deferred (ADR-020).
- Which pairwise aggregation method (ADR-009) to use when all dimensions are scored jointly. Resolved →
  no ideal / deferred (ADR-020).
