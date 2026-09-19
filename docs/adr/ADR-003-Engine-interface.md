---
name: Engine integration via OpenAI-compatible API
type: decision
status: accepted
date: 2026-09-19
summary: Integrate inference engines (vLLM, llama.cpp, Ollama, Transformers) through the OpenAI-compatible API.
---

# ADR-003: Engine interface — OpenAI-compatible API

## Context

ADR-001 introduced an engine plugin interface so the same model could be compared across engines.
To make that comparison uniform and ergonomic, every engine must be reachable through a single,
standard interface. The candidate engines — vLLM, llama.cpp, Ollama, and HuggingFace Transformers —
all expose an **OpenAI-compatible** `/v1/chat/completions` endpoint.

## Decision

Standardize the engine interface on the **OpenAI-compatible API**. Every engine plugin talks to its
target through `/v1/chat/completions` (with seeded sampling), and the benchmark runner talks to
engines through one shared client.

## Consequences

- **Uniform client.** One client class drives all engines, so benchmark code does not branch on
  engine type.
- **Direct engine comparison.** The core use case ("same model, two engines — same result?") becomes
  a single API call per engine, with seeded sampling for reproducibility.
- **Portability.** The same client works against any OpenAI-compatible server, including the judge
  model (see ADR-005).
- **Loss of engine-specific features.** Non-standard endpoints, custom tokenizers, or advanced
  engine-only flags are not exposed; if needed later, a second interface layer can be added.

## Supported engines

| Engine | OpenAI-compatible endpoint | Notes |
|--------|---------------------------|-------|
| vLLM | `POST /v1/chat/completions` | Full-featured, high-throughput serving. |
| llama.cpp | `POST /v1/chat/completions` | `openai_server` mode. |
| Ollama | `POST /v1/chat/completions` | Built-in OpenAI compatibility. |
| Transformers | `OpenAIWrapper` | In-process, no separate server. |

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. OpenAI-compatible API | Single standard interface across engines | Uniform, portable, all engines support it | Misses engine-specific features |
| B. Native engine interface | Call each engine's native API directly | Full feature access | No uniform client, complex per-engine code |
| C. vLLM-only | Standardize on vLLM exclusively | One implementation to maintain | Excludes other engines the project wants to compare |
| D. Raw HTTP passthrough | Call each engine's native HTTP endpoint | Direct | Every engine gets bespoke code |

Option A balances uniformity and portability while leveraging support already built into every
engine. Option B/D reintroduce per-engine complexity; Option C contradicts the engine-comparison
pillar.

## Open points

- Whether to standardize on the chat completions endpoint or also adopt the OpenAI-compatible
  embeddings (`/v1/embeddings`) endpoint for similarity-based metrics. No preference expressed;
  deferred for future optimization.
- Streaming responses adopted for token-level latency measurement (ADR-007).
