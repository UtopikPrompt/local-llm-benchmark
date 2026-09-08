# local-llm-benchmark

Benchmark **local** LLM engines (e.g. [Ollama](https://ollama.com), [LM Studio](https://lmstudio.ai)) with a **fixed** model, and visualize the results in a browser.

The model is the *constant*; the engine is the *variable under test*. For each task the benchmark measures **speed** (time-to-first-token, throughput, iterations-per-second) and **quality** (deterministic checks plus an optional judge model), then writes a CSV/JSON report and renders a dashboard.

## How it works

```
engine ──▶ speed (ttft/tok/s/iters/s) ──▶ judge ──▶ quality ──▶ Row
   ▲                                              │
   └───────────── quality_passed ◀────────────────┘
```

- **Engines under test** — OpenAI-compatible HTTP servers (Ollama, LM Studio, …).
- **Tasks** — a fixed corpus of prompts (system + user) with an expected answer.
- **Judge** — an optional second model that scores output quality.
- **Reporter** — aggregates results into CSV/JSON and prints a summary.

## Layout

```
src/local_llm_benchmark/
├── config.py          # EngineConfig / JudgeConfig / BenchmarkConfig + YAML/JSON I/O
├── tasks/
│   └── corpus.py      # Task dataclass + the built-in task corpus
├── engines/
│   ├── base.py        # Engine interface
│   └── openai_compat.py# OpenAI-compatible HTTP client
├── benchmarks/
│   └── speed.py        # benchmark_speed()
├── eval/
│   └── quality.py      # Judge interface + evaluate_quality()
├── report/
│   └── report.py       # CSV/JSON writer + print_summary()
├── ui/
│   ├── app.py          # FastAPI JSON API + static dashboard
│   ├── proxy.py        # OpenAI-compatible serving proxy
│   └── dashboard.html  # front-end
├── results.py          # Row dataclass + CSV column constants
└── runner.py           # async orchestrator + CLI entrypoint
```

## Installation

```bash
# from the project root
pip install -e ".[dev]"
```

This installs the runtime dependencies (`fastapi`, `httpx`, `anyio`, `pydantic`, `PyYAML`) plus the dev tooling (`pytest`, `ruff`).

## Quick start

Start an OpenAI-compatible engine (e.g. Ollama) and pull a model:

```bash
ollama serve
ollama pull llama3
```

Run the benchmark against it:

```bash
python -m local_llm_benchmark.runner \
    --base-url http://localhost:11434 \
    --model llama3 \
    --format csv \
    --output results.csv
```

Or use a configuration file:

```bash
python -m local_llm_benchmark.runner --config config.yaml --serve
```

A template is included at [`config.example.yaml`](config.example.yaml). Copy it to `config.yaml`, edit the values, and pass `--config config.yaml` (or `--config config.example.yaml`).

## Configuration

A configuration file is either JSON or YAML (JSON is a subset of YAML, so the loader sniffs the format automatically).

```yaml
engines:
  - name: Ollama
    base_url: http://localhost:11434   # must be an absolute http(s) URL
    model: llama3
    timeout: 60.0                      # per-request timeout in seconds
    max_concurrent: 1                  # max concurrent requests per task

judges:
  - name: judge
    base_url: http://localhost:11434
    model: llama3                      # optional quality judge

tasks: tasks/                          # directory of task files (defaults to "." = built-in corpus)
task: my-task-id                       # optionally run a single task by id
max_concurrent: 1                      # max concurrent engine requests globally
timeout: 60.0
format: csv                            # "json" or "csv"
output: results.csv
```

### Report columns

The report keeps the columns required by the spec:

| Column | Description |
| --- | --- |
| `engine` | Engine name |
| `model` | Model served by the engine |
| `judge` | Judge name |
| `task_id` | Task identifier |
| `category` | Task category |
| `ttft_s` | Time-to-first-token (seconds) |
| `tok_per_s` | Tokens per second |
| `iters_per_s` | Iterations per second |
| `quality_passed` | Whether the output satisfied all quality checks |
| `quality_deterministic` | Whether deterministic checks passed |
| `quality_judge` | Judge score (when a judge is used) |
| `quality_note` | Additional judge/quality notes |

## Web dashboard

The same benchmark can be served through a FastAPI app with an embedded browser dashboard.

```bash
# run the API + dashboard on 127.0.0.1:8000
uvicorn local_llm_benchmark.ui.app:run_server --host 127.0.0.1 --port 8000
```

Open the dashboard at <http://127.0.0.1:8000> and click **Run** to benchmark the running engine. The dashboard sends a JSON body to `POST /run`:

```json
{
  "base_url": "http://localhost:11434",
  "model": "llama3",
  "judgeUrl": true,
  "judgeModel": "llama3",
  "task_dir": "tasks",
  "timeout": 60,
  "output": "results.json"
}
```

The dashboard also exposes:

- `GET /` — the dashboard.
- `POST /config` — preview engines/models for a candidate configuration.
- `POST /models` — list models advertised by an engine at a base URL.
- `GET /results/{name}` — stream a saved report.

## Development

```bash
# run the test suite
pytest

# lint / format
ruff check .
ruff format .
```

## License

MIT
