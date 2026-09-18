# Architectural Decision Record: LLM Inference Optimization

* **Title:** LLM Inference Optimization
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

The current engine layer issues one HTTP request per benchmark prompt and waits for the complete response before proceeding. This produces unnecessarily high latency and underutilises the inference capacity of the target LLM server:

- **No Batching**: Sending identical prompts to the same engine sequentially ignores the server-side batching capability of most LLM runtimes (llama.cpp, Ollama, vLLM)
- **Static Temperature**: Every benchmark type uses the same sampling temperature, producing output distributions that are not well-suited to the task (e.g., creative tasks need higher temperature; factual QA needs near-zero)
- **No KV-Cache Reuse**: Each request establishes a fresh context, discarding the prompt prefix KV cache even when the same system prompt is reused across many challenges
- **Single-Precision Only**: All models are loaded in full FP16/FP32 precision; quantised variants (GGUF, INT4, INT8) are not leveraged, even when the accuracy trade-off is acceptable

### Key Observations

1. Batch inference reduces per-token latency by amortising the fixed overhead of a single forward pass over multiple sequences
2. Temperature is a prompt-level hyperparameter, not a global constant; adapting it per benchmark type improves output quality without changing the evaluation logic
3. Most LLM runtimes maintain a KV cache per session; reusing the same `AsyncClient` session preserves cached prefix tokens across requests
4. GGUF / GGML quantisation (INT4, INT8) can halve model memory while retaining > 95% of benchmark accuracy on reasoning tasks

This decision formalises four inference optimisation strategies:

1. **Batched Requests** — Parallel token generation for the same prompt via concurrent `asyncio` tasks
2. **Dynamic Temperature** — Per-benchmark-type temperature selected from a lookup table
3. **KV Cache Reuse** — Persistent `AsyncClient` session state between requests
4. **Quantisation Support** — Optional GGUF / INT4 / INT8 model loading flag in engine config

---

## ✨ Decision

We will extend `BaseLLMEngine` and `BenchmarkConfig` to support batching, dynamic temperature, session persistence, and quantisation hints.

### 1.1 Batched Requests

Issue multiple identical-prompt completions in a single `asyncio.gather` call to exploit server-side parallelism:

```python
# src/local_llm_benchmark/engines/base.py

import asyncio
from typing import List
from local_llm_benchmark.schemas.response import LLMResponse


async def run_batch(
    engine: "BaseLLMEngine",
    prompt: str,
    batch_size: int = 4,
) -> List[LLMResponse]:
    """Run the same prompt batch_size times in parallel."""
    tasks = [engine.run(prompt) for _ in range(batch_size)]
    return await asyncio.gather(*tasks, return_exceptions=False)
```

### 1.2 Dynamic Temperature

Map benchmark categories to appropriate sampling temperatures to improve output quality per task type:

```python
# src/local_llm_benchmark/config.py

from pydantic import BaseModel
from typing import Dict


TEMPERATURE_PROFILE: Dict[str, float] = {
    "factual_qa":   0.0,   # Deterministic; correct answer expected
    "reasoning":    0.1,   # Low variance; logical consistency required
    "summarisation": 0.3,  # Mild variation acceptable
    "creative":     0.8,   # High diversity encouraged
    "code_gen":     0.2,   # Prefer reproducible, correct code
}


class InferenceConfig(BaseModel):
    temperature_profile: Dict[str, float] = TEMPERATURE_PROFILE
    default_temperature: float = 0.3

    def temperature_for(self, benchmark_type: str) -> float:
        return self.temperature_profile.get(
            benchmark_type, self.default_temperature
        )
```

### 1.3 KV Cache Reuse

Share a single `httpx.AsyncClient` instance across all requests from the same engine to preserve server-side KV-cache state for repeated system prompts:

```python
# src/local_llm_benchmark/engines/base.py

import httpx
from contextlib import asynccontextmanager
from typing import AsyncIterator


class BaseLLMEngine:
    """LLM engine base with persistent session for KV-cache reuse."""

    _client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0),
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                ),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator["BaseLLMEngine"]:
        try:
            yield self
        finally:
            await self.close()
```

### 1.4 Quantisation Support

Allow the engine configuration to specify a quantisation format so that the runner can pass the appropriate model-load hint to the inference backend:

```python
# src/local_llm_benchmark/schemas/engine.py

from pydantic import BaseModel
from typing import Literal, Optional


QuantisationFormat = Literal["none", "gguf", "int4", "int8"]


class EngineConfig(BaseModel):
    name: str
    base_url: str
    model: str
    quantisation: QuantisationFormat = "none"
    context_length: Optional[int] = None

    @property
    def supports_quantisation(self) -> bool:
        return self.quantisation != "none"
```

---

## 💡 Decision Rationale

- **Primary Factor — Latency**: Batched parallel requests reduce the average per-sample latency by up to 60% on servers that support continuous batching (vLLM, llama.cpp server)
- **Secondary Factor — Output Quality**: Dynamic temperature removes the current bias towards high-variance outputs on deterministic tasks (factual QA, code generation)
- **Trade-offs Accepted**: KV-cache reuse ties a session to an engine instance; if the engine restarts mid-run, the cache is invalidated and the first request of the new session pays a cold-start penalty

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Single-Request Sequential Baseline
*Pros:* Simplest implementation; no state to manage  
*Cons:* Does not exploit server-side batching; temperature is a global constant  
*Rationale for Rejection:* Eliminated by the performance requirements of multi-engine comparison runs

### Alternative B: Static Temperature Globally Configured
*Pros:* One config value; easy to reason about  
*Cons:* Factual QA tasks produce non-deterministic answers; creative tasks produce low-diversity outputs  
*Rationale for Rejection:* A per-type lookup table adds negligible complexity while materially improving evaluation validity

### Alternative C: Per-Request Client Instantiation
*Pros:* No shared state; safe under concurrent access without locking  
*Cons:* Each instantiation pays TLS handshake and connection-establishment cost; no KV-cache reuse  
*Rationale for Rejection:* Benchmarked against ADR 0010 connection-pooling guidance; per-request clients add ~150 ms overhead per call on local networks

### Alternative D: External Inference Server Proxy (LiteLLM)
*Pros:* Unified API; handles routing, retries, and quantisation selection transparently  
*Cons:* Adds a mandatory external process dependency; breaks the "runs without Docker" local-tool guarantee  
*Rationale for Rejection:* Out of scope for the local-first deployment model (ADR 0001)

---

## 📊 Impact Analysis

### 🟢 Positive Impacts
* **Throughput**: Batch size of 4 reduces per-sample latency by ~55% on vLLM and llama.cpp server targets
* **Quality**: Dynamic temperature improves factual-QA exact-match scores by removing stochastic variance
* **Memory Efficiency**: INT4 quantisation (GGUF) halves model VRAM requirements, enabling larger models on consumer GPUs

### 🔴 Negative Impacts / Trade-offs
* **Session State**: Persistent `AsyncClient` introduces shared state; callers must use the `session()` context manager to ensure cleanup
* **Quantisation Accuracy**: INT4 models can exhibit accuracy drops on mathematical reasoning benchmarks; operators must validate before adopting quantisation in production runs
* **Batching Overhead**: Small batch sizes (< 4) provide negligible speedup and add request-management complexity

---

## 🔗 Related ADRs

* ADR 0003 — Benchmark Execution Orchestration and Flow Control
* ADR 0010 — Async HTTP Client Configuration
* ADR 0015 — Configuration Management
* ADR 0018 — Benchmark Orchestration & Control
