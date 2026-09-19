# Module — quality metrics, comparison, gating

## Dimensions (full set)

- **accuracy** (exact-match EM + F1 on static datasets)
- **groundedness** (RAGAS groundedness / GEA)
- **reasoning / complexity**
- **instruction-following**
- **relevance**
- **harmfulness / safety**
- **faithfulness**

## Scoring

- **Hybrid scoring** (ADR-016): dimensions with strong exact-match signal (e.g. reasoning) use a
  static + judge hybrid. No dimension is policy-gated — every dimension follows the same scoring
  approach.
- **Gating** (ADR-017) is left to the **runtime/user** decision, not baked into policy.
- **Weighting / aggregation** is **deferred** (ADR-020) — there is "no ideal" yet. Keep aggregation
  flexible; do not hardcode a single weighting scheme.

## Comparison

- **LLM-as-judge** (ADR-005): structured outputs for deterministic, comparable verdicts.
- **Pairwise comparison** (ADR-009) reduces judge variance. It is **O(n²)**, so candidate counts are
  **capped** per benchmark (ADR-013, default cap ~10).
- **Candidate gating** (ADR-017) is a runtime/user concern.

## Guardrails

- Implement all dimensions from the full set; do not drop one without an explicit decision.
- Do not hardcode weighting/aggregation (deferred).
- Do not bypass the pairwise cap — respect that comparison is O(n²).
- Never gate a dimension by policy; leave gating to the runtime/user.
