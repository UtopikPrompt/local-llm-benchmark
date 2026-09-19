---
name: Complete benchmark — adopt all candidate quality dimensions
type: decision
status: accepted
date: 2026-09-19
summary: Adopt all candidate third dimensions (reasoning, instruction-following, relevance, harmfulness, faithfulness) and measure them via LLM-as-judge, reusing the same datasets/prompts as the other dimensions.
---

# ADR-012: Quality metrics — adopt all candidate dimensions

## Context

ADR-008 decided to add a third quality dimension to complete the benchmark, listing candidates:
reasoning/complexity, instruction-following, relevance, harmfulness/safety, and a broader
faithfulness signal. Two open points remained: which specific dimension(s) to adopt, and whether
to measure the third dimension statically or via LLM-as-judge (ADR-005).

## Decision

**Adopt all candidate dimensions** rather than a single one. The benchmark should measure
reasoning/complexity, instruction-following, relevance, harmfulness/safety, and faithfulness.

- **Datasets/prompts:** Reuse the same datasets and prompt structure as the accuracy and
  groundedness dimensions ("like other dimensions"). Dimensions that are inherently judge-based
  (e.g., instruction-following, relevance, faithfulness) use the same prompt-driven approach as
  LLM-as-judge (ADR-005).
- **Measurement:** Measure all dimensions **via LLM-as-judge**, consistent with the benchmark's
  quality methodology (ADR-005). Where a dimension has a strong exact-match signal (e.g., reasoning
  on GSM8K-style tasks), the exact-match/F1 metric (ADR-004) may supplement the judge score.

## Consequences

- **Complete coverage.** The benchmark spans correctness, RAG faithfulness, reasoning, adherence,
  relevance, safety, and broader faithfulness — matching the "complete benchmark" goal.
- **Consistency.** All judge-based dimensions share one methodology (pairwise comparison, ADR-009)
  and one client (ADR-003), simplifying implementation.
- **Higher setup cost.** More judge prompts, more data to aggregate, and more variance to manage
  across dimensions. Dimensions with high judge disagreement (e.g., harmfulness) may need extra
  sampling or guardrails.
- **Broader aggregation.** Pairwise comparison (ADR-009) must handle more candidates per benchmark;
  the aggregation method (ADR-009's open point) must scale to all dimensions jointly.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. All candidate dimensions | Measure every dimension via LLM-as-judge | Complete coverage, consistent method | Higher setup cost, more variance |
| B. Single best dimension | Pick the strongest candidate only | Simpler, focused | Incomplete benchmark |
| C. Mix static + judge | Some dimensions static, some judged | Cheaper per dimension | Inconsistent methodology |

Option A delivers the "complete benchmark" the project targets with one consistent methodology.
Option B is too narrow given the explicit completeness goal; Option C introduces methodology
inconsistency the project wants to avoid.

## Open points

- Whether any dimension (e.g., harmfulness/safety) requires policy gating or special handling.
  Resolved → no dimension requires policy gating (ADR-016).
- Whether dimensions with strong exact-match signals (reasoning) should use a hybrid static + judge
  score rather than judge-only. Resolved → hybrid static + judge for such dimensions (ADR-016).
- Which pairwise aggregation method (ADR-009) to use when all dimensions are scored jointly. No
  preference expressed; deferred for future optimization.
