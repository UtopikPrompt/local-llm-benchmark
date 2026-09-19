---
name: Quality comparison — pairwise judge
type: decision
status: accepted
date: 2026-09-19
summary: Use pairwise comparison for LLM-as-judge scoring to reduce variance.
---

# ADR-009: Quality comparison — pairwise judge

## Context

ADR-005 established LLM-as-judge scoring with structured outputs. To reduce judge variance (LLM
judges are not perfectly reliable), the comparison method was left open. The user chose **pairwise**
comparison over absolute scoring.

## Decision

Use **pairwise comparison** for open-ended quality. For each candidate output, the judge is asked to
rank/order a pair (e.g., "which of A or B is more helpful?") rather than assign an absolute score.

## Consequences

- **Lower variance.** Pairwise comparisons are less sensitive to absolute thresholds, so judges are
  less likely to disagree across absolute ratings.
- **Relative, not absolute.** Results are relative rankings/odds, not absolute scores — useful for
  "which is better?" but not for ranking against a fixed scale.
- **More comparisons.** Full pairwise evaluation is O(n²) comparisons for `n` candidates, which can
  be expensive at scale.
- **Aggregation.** Pairwise results can be aggregated (e.g., via a ranking method such as
  pairwise/Bradley-Terry/Maximally Informative) into a preference order.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Pairwise comparison | Judge ranks pairs of outputs | Lower variance, robust | O(n²) comparisons at scale |
| B. Absolute scoring | Judge assigns a score per output | Simpler, absolute ranking | Higher variance, threshold-sensitive |
| C. Ensemble of both | Absolute + pairwise | Robust, cross-validation | More cost/complexity |

Option A best matches the goal of reducing judge variance. Option B is more variance-prone; Option C
adds cost and complexity for marginal gains once the core is validated.

## Open points

- Whether to aggregate pairwise results via a specific ranking method (e.g., Bradley-Terry,
  Plackett-Luce, or majority voting). No preference expressed; deferred for future optimization.
- Whether to cap the number of candidates evaluated pairwise per benchmark to bound cost. Resolved
  → cap candidates per benchmark (ADR-013).
- Whether sample count (ADR-005) will be tuned later to optimize statistical significance. No
  preference expressed; deferred for future optimization.
