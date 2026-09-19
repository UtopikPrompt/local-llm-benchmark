---
name: Quality comparison — runtime-configurable candidate gating
type: decision
status: accepted
date: 2026-09-19
summary: Which candidates remain within the pairwise cap is decided by the user at runtime (not hardcoded), so the filter is configurable per run.
---

# ADR-017: Quality comparison — user-decided candidate gating

## Context

ADR-013 decided to **cap** the number of candidates evaluated pairwise per benchmark, and noted that
an initial filter/ranking decides which candidates remain within the cap. One open point concerned
whether to **gate which candidates remain within the cap** (e.g., an accuracy/groundedness filter)
and how that filter is defined.

## Decision

**Decide candidate gating at runtime, by the user.** Rather than hardcoding a specific filter
(e.g., "drop candidates below accuracy 0.8"), the benchmark lets the user define the gating filter
per run.

- **No default filter required.** Runs may proceed with no gating (all candidates within the cap)
  or with a user-specified filter (e.g., accuracy/groundedness thresholds).
- **Configurable filter.** The gating criteria (which metrics, thresholds) are benchmark options,
  consistent with the cap itself (ADR-013).

## Consequences

- **Flexibility.** Users can gate to retain only strong candidates, or disable gating to evaluate
  every model within the cap, depending on the goal.
- **No coupling.** A single "correct" filter isn't imposed, avoiding overfitting gating to one
  dataset/metric.
- **Consistency.** Gating is expressed as the same config surface as the cap and other benchmark
  options (ADR-013, ADR-010).

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. User-decided gating | Filter is configurable per run | Flexible, no coupling | More setup per run |
| B. Hardcoded filter | Fixed accuracy/groundedness thresholds | Simple, predictable | Overfits to one metric |
| C. No gating | All candidates within cap | Simple | May include weak candidates |

Option A matches the project's flexible, user-driven philosophy. Option B imposes a single opinion;
Option C ignores the cost-benefit of gating.

## Open points

- Whether a default gating template (e.g., accuracy + groundedness) should be offered for convenience.
- Whether to expose the gating filter as a CLI flag and UI setting (ADR-013, ADR-010).
