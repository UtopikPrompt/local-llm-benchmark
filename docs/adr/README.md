# Architecture Decision Records

This directory contains architecture decision records (ADRs) for the project.

| Number | Summary | Status | Date |
|--------|---------|--------|------|
| [ADR-001](./ADR-001-Project-foundation.md) | Foundational scope, architecture, and design principles for the local LLM benchmarking project | Accepted | 2026-09-19 |
| [ADR-002](./ADR-002-UI-stack.md) | Standardize the web UI on Astro, a buildless JavaScript framework | Accepted | 2026-09-19 |
| [ADR-003](./ADR-003-Engine-interface.md) | Integrate inference engines via the OpenAI-compatible API | Accepted | 2026-09-19 |
| [ADR-004](./ADR-004-Quality-metrics.md) | Adopt accuracy and groundedness as the quality metrics | Accepted | 2026-09-19 |
| [ADR-005](./ADR-005-Quality-comparison.md) | Compare open-ended quality using an LLM-as-judge | Accepted | 2026-09-19 |
| [ADR-006](./ADR-006-UI-runtime.md) | Expose interactive benchmark runs in the UI via Astro server actions | Accepted | 2026-09-19 |
| [ADR-007](./ADR-007-Engine-streaming.md) | Support streaming responses for token-level latency measurement | Accepted | 2026-09-19 |
| [ADR-008](./ADR-008-Quality-third-dimension.md) | Add a third quality dimension for a complete benchmark (specific dimension still open) | Accepted | 2026-09-19 |
| [ADR-009](./ADR-009-Quality-pairwise.md) | Use pairwise comparison for LLM-as-judge scoring to reduce variance | Accepted | 2026-09-19 |
| [ADR-010](./ADR-010-UI-cache-and-api.md) | Cache interactive results (gitignored) and add an API route for remote/headless runs | Accepted | 2026-09-19 |
| [ADR-011](./ADR-011-Streaming-offline-storage.md) | Store streamed token timings offline for analysis (not on-the-fly only) | Accepted | 2026-09-19 |
| [ADR-012](./ADR-012-Quality-all-dimensions.md) | Adopt all candidate quality dimensions, measured via LLM-as-judge, reusing other dimensions' datasets/prompts | Accepted | 2026-09-19 |
| [ADR-013](./ADR-013-Quality-cap-candidates.md) | Cap the number of candidates evaluated pairwise per benchmark to bound O(n²) cost | Accepted | 2026-09-19 |
| [ADR-014](./ADR-014-UI-cache-lifecycle.md) | Set a maximum cache size (LRU eviction) and tag cached results with model/engine version for staleness | Accepted | 2026-09-19 |
| [ADR-015](./ADR-015-Streaming-storage-format.md) | Prefer Parquet for token-timing storage; add a retention policy for stored timings, disabled by default | Accepted | 2026-09-19 |
| [ADR-019](./ADR-019-Streaming-storage-schema.md) | Adopt token-level rows + run-level metadata schema; DuckDB backend; age-based retention | Accepted | 2026-09-19 |
| [ADR-016](./ADR-016-Quality-hybrid-scoring.md) | Use hybrid static + judge scoring for strong exact-match dimensions (e.g., reasoning); no dimension policy-gated | Accepted | 2026-09-19 |
| [ADR-020](./ADR-020-Quality-hybrid-deferred.md) | Defer (no ideal) hybrid dimension qualification, static+judge weighting/aggregation, and pairwise aggregation | Accepted | 2026-09-19 |
| [ADR-017](./ADR-017-Quality-gating.md) | Decide candidate gating within the pairwise cap at runtime, by the user; expose the cap as a CLI/UI setting | Accepted | 2026-09-19 |
| [ADR-018](./ADR-018-UI-cache-eviction-identity.md) | Eviction considers result age; version tags include judge model/seed; API route shares the cache | Accepted | 2026-09-19 |
