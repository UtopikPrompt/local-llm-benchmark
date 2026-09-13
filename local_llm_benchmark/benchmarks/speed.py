"""Speed benchmark: measure streaming throughput of an engine.

Measures three things per task:

* **TTFT** (time-to-first-token): wall-clock time from request to the first
  token.
* **tok/s**: tokens per second, computed from the number of generated tokens
  and the total generation time.
* **iters/s**: iterations (requests) per second, computed from the number of
  trials and the total wall-clock time.

The model is remote, so the local GIL/GC never limits the measurement; async
streaming requests give true throughput.
"""

from __future__ import annotations

import anyio
import time
from typing import List

from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.results import Row


async def benchmark_speed(
    engine: Engine,
    task: object,
    *,
    max_tokens: int = 64,
    trials: int = 3,
    max_concurrent: int = 1,
) -> List[Row]:
    """Benchmark *engine* on *task* over *trials* concurrent requests.

    Args:
        engine: The engine under test.
        task: The task to run.
        max_tokens: Maximum tokens to generate per request.
        trials: Number of concurrent trials.
        max_concurrent: Maximum concurrent requests per task.

    Returns:
        One :class:`Row` per trial, each with speed statistics.
    """
    prompt = getattr(task, "prompt", "")
    system = getattr(task, "system", None)
    messages: List[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    rows: List[Row] = []
    start = time.perf_counter()
    semaphore = anyio.Semaphore(max_concurrent)

    async def _run() -> Row:
        async def _stream() -> tuple[int, float]:
            tokens = 0
            ttft = 0.0
            first = time.perf_counter()
            async for token in engine.chat(messages, max_tokens=max_tokens, stream=True):
                tokens += 1
                if tokens == 1:
                    ttft = time.perf_counter() - first
            return tokens, ttft

        async with semaphore:
            t0 = time.perf_counter()
            tokens, ttft = await _stream()
            elapsed = time.perf_counter() - t0
            return Row(
                engine=engine.config.name,
                model=engine.config.model,
                task_id=getattr(task, "id", ""),
                category=getattr(task, "category", "").value if hasattr(task, "category") else "",
                prompt=prompt,
                ttft_s=ttft,
                tok_per_s=tokens / elapsed if elapsed > 0 else 0.0,
                iters_per_s=1.0 / elapsed if elapsed > 0 else 0.0,
            )

    for _ in range(trials):
        await _run()

    total_elapsed = time.perf_counter() - start
    for row in rows:
        row.iters_per_s = trials / total_elapsed if total_elapsed > 0 else 0.0
    return rows
