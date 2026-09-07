"""local-llm-benchmark.

Benchmark local LLM engines (models run *server-side* on Ollama/LM Studio) and
visualize the numbers in a browser.

The architecture keeps all heavy work server-side:

Browser (HTML/CSS/JS) ── fetch() ──▶ FastAPI server (async, JSON API + static page)
                                      │  POST /run  → run_benchmark()
                                      ▼
                                local_llm_benchmark.runner
                                      │
                       ┌──────────────┴──────────────┐
                       │                              │
              benchmark_speed() streaming       evaluate_quality()
              tok/s, TTFT, iters/s              deterministic + judge
                       └───────────────┬──────────────┘
                                      ▼
                              OpenAICompatEngine
                    (httpx streaming POST /chat/completions)
                                      ▼
                              Ollama / LM Studio engine
                              (the variable under test)
"""

__version__ = "0.1.0"
