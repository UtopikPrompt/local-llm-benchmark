---
name: Quality hybrid scoring — weighting, dimension qualification, and aggregation deferred
type: decision
status: accepted
date: 2026-09-19
summary: Defer (no ideal) the qualification of hybrid dimensions, the weighting/aggregation of static+judge scores, and the pairwise aggregation method.
---

# ADR-020: Quality hybrid scoring — deferred decisions

## Context

ADR-016 decided that dimensions with a strong exact-match signal (e.g., reasoning) use a hybrid
static + judge score, while other dimensions remain judge-only. Three open points concerned the
details of the hybrid approach:

- Which dimensions qualify as "strong exact-match signal" and use the hybrid (beyond reasoning).
- How to weight/aggregate the static and judge scores for hybrid dimensions.
- Which pairwise aggregation method (ADR-009) to use when all dimensions are scored jointly.

## Decision

- **No ideal (deferred).** There is no ideal choice yet for any of the three questions; each is
  deferred to when the project needs a concrete implementation.
  - **Hybrid dimension qualification.** No definitive list of dimensions beyond reasoning is
    established. Any future dimension that exhibits a strong exact-match signal can be added to the
    hybrid set, and the set can be re-evaluated as new datasets/dimensions are considered.
  - **Static + judge weighting.** No fixed weighting or aggregation of the static and judge scores
    is set. The weighting can be tuned per dimension (and possibly per benchmark) once data is
    available to balance the objective and qualitative signals.
  - **Pairwise aggregation.** No pairwise aggregation method is chosen yet for jointly scoring all
    dimensions (ADR-009). The method can be selected when the project moves to a concrete
    multi-dimension comparison.

## Consequences

- **Flexibility.** Deferring keeps the hybrid approach configurable as the dimension set and
  datasets evolve, rather than locking in choices that may not suit the data.
- **No premature lock-in.** We avoid committing to a weighting or aggregation scheme that could be
  superseded by a better-fitting method once the toolchain and datasets are fixed.
- **Consistency preserved.** Regardless of how these are eventually resolved, only dimensions with
  a strong exact-match signal use the hybrid; others remain judge-only.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Defer (no ideal) | Leave each question open | Flexible, avoids premature lock-in | No concrete method until implementation |
| B. Fix a global weight | One static+judge weight for all | Simple, reproducible | May not fit every dimension |
| C. Fixed aggregation now | Pick one pairwise method immediately | Decisive | May be suboptimal for the data |

Option A keeps the hybrid scoring adaptable; B and C risk committing to a scheme that may not fit
the eventual datasets and dimensions.

## Open points

- None.
