# Module — storage & streaming

## Streaming (ADR-007)

- **SSE** streaming of token-level output.
- Reports **per-token latency** and **TTFT** (time-to-first-token).

## Storage format

- **Token-level Parquet**: per-token outputs and timing.
- **Run-level metadata**: columns describing the run (engine, model, benchmark, seed, judge, ...).
- **One Parquet file per run.**
- Analysis backend is **DuckDB**.

## Retention

- Age-based retention policy; **disabled by default**.

## Guardrails

- Keep token-level and run-level data in their respective layers.
- Streaming is about latency instrumentation (per-token timing + TTFT), not just output delivery.
- Do not change the storage layout away from Parquet + run-level metadata without a decision.
