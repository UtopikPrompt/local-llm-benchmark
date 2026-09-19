---
name: Engine interface — streaming for token-level latency
type: decision
status: accepted
date: 2026-09-19
summary: Enable streaming responses to measure token-level latency.
---

# ADR-007: Engine interface — support streaming responses

## Context

ADR-003 standardized the engine interface on the OpenAI-compatible API. Two open points remained,
one of which concerns measuring latency at token granularity. To answer *"how fast does this model
actually produce tokens over time?"* rather than only end-to-end latency, the engine interface must
support **streaming** responses.

## Decision

Support **streaming responses** for `/v1/chat/completions` on every engine. The client streams
tokens as they arrive (SSE) and the benchmark runner consumes the stream to compute per-token
latency and time-to-first-token (TTFT).

## Consequences

- **Token-level latency.** Per-token timing and TTFT are measurable, giving a fuller latency picture
  than end-to-end wall-clock alone.
- **Live UX.** Streaming underpins the real-time feedback of the interactive UI (ADR-006).
- **Single interface.** Streaming is handled by one client method, so engine plugins share it.
- **Extra data.** More data to process and store; responses need a streaming-aware parser.

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Streaming responses | SSE streaming, per-token timing + TTFT | Token-level latency, powers live UX | More data to process |
| B. Non-streaming only | Single end-to-end response | Simplest, less data | Only end-to-end latency, no TTFT |
| C. Streaming for UI only | Stream in UI, batch in CLI | Live UX without CLI overhead | Two code paths, inconsistent metrics |

Option A gives the richest latency signal and powers the interactive UI with one code path. Option
B is too coarse for the project's latency focus; Option C duplicates logic and risks metric
inconsistency.

## Open points

- Store streamed token timings for offline analysis (ADR-011).
- Whether to also stream `/v1/embeddings` for real-time latency measurement. No preference
  expressed; deferred for future optimization.
