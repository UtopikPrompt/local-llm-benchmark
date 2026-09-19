---
name: Quality comparison — cap candidates per benchmark
type: decision
status: accepted
date: 2026-09-19
summary: Cap the number of candidates evaluated pairwise per benchmark to bound O(n²) comparison cost.
---

# ADR-013: Quality comparison — cap pairwise candidates per benchmark

## Context

ADR-009 chose pairwise comparison for LLM-as-judge scoring. Full pairwise evaluation is O(n²)
comparisons for `n` candidates, which becomes expensive as the number of models grows. One open
point concerned whether to **cap the number of candidates** evaluated pairwise per benchmark to bound
this cost.

## Decision

**Cap the number of candidates evaluated pairwise per benchmark.** Each benchmark evaluates at most
a fixed maximum number of candidates (e.g., a default cap of 10, configurable per benchmark) before
pairwise evaluation.

- **Cost bound.** Caps the O(n²) comparison count, keeping benchmarks tractable regardless of how
  many models are run.
- **Configurable.** The cap is a benchmark parameter, so users can widen it for small candidate sets
  or narrow it for large comparisons.
- **Completeness trade-off.** Only the top candidates (by an initial filter/ranking, or a random
  subset) may be evaluated; this trades off evaluating every model for manageable cost.

## Consequences

- **Bounded runtime.** Pairwise evaluation time stays roughly linear in the cap, not quadratic in
  candidate count.
- **Config surface.** The cap must be exposed as a benchmark option (CLI flag / UI setting).
- **Initial ranking.** To decide which candidates to keep within the cap, an initial filter (e.g.,
  accuracy/groundedness gating) should be defined so the cap retains the strongest candidates.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Cap candidates per benchmark | Fixed max candidates (configurable) | Bounded cost, tractable | May miss weaker models |
| B. No cap (all candidates) | Evaluate every model pairwise | Complete comparison | O(n²) cost explodes |
| C. Dynamic cap | Scale cap by candidate quality/runtime | Adaptive cost | More complexity, nondeterminism |

Option A bounds cost while remaining simple and configurable. Option B risks runaway cost; Option
C adds complexity before the core is validated.

## Open points

- Whether to gate which candidates remain within the cap (e.g., accuracy/groundedness filter) and
  how the filter is defined. Resolved → decide gating at runtime, by the user (ADR-017).
- Whether to randomize the subset within the cap for reproducibility or to allow coverage. No
  preference expressed; deferred for future optimization.
- Whether to expose the cap as a CLI flag and UI setting (ADR-010). Resolved → yes (ADR-017).
