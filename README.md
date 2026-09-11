# local-llm-benchmark

Benchmark **local** LLM engines (e.g. [Ollama](https://ollama.com), [LM Studio](https://lmstudio.ai)) with a **fixed** model, and visualize the results in a browser.

The model is the _constant_; the engine is the _variable under test_. For each task the benchmark measures **speed** (time-to-first-token, throughput, iterations-per-second) and **quality** (deterministic checks plus an optional judge model), then renders a dashboard.

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
src/
├── app.ts / app.html / app.d.ts   # SvelteKit app entry, types, globals
├── lib/
│   ├── config.ts                  # EngineConfig / JudgeConfig / BenchmarkConfig + DEFAULTS
│   ├── engines/                   # engine interface, client, judge, models, compat
│   │   ├── engines.ts              # Engine interface
│   │   ├── index.ts                # makeEngine() / loadEngines() / saveEngines()
│   │   ├── judge.ts                # Judge interface
│   │   ├── models.ts               # listModels()
│   │   └── openai_compat.ts        # OpenAI-compatible HTTP client
│   ├── storage/                   # IndexedDB (idb): engines, models, results, corpus
│   │   ├── db.ts                   # indexedDB wrappers
│   │   └── index.ts                # save/load/delete/append for each store
│   ├── tasks.ts                   # Task dataclass + built-in corpus
│   ├── quality.ts                 # Judge interface + evaluate_quality()
│   ├── report.ts                  # write_csv / write_json
│   ├── runner.ts                  # async orchestrator (benchmark_speed, concurrency)
│   ├── benchmark.ts               # TTFT / tok/s / iters/s measurement
│   ├── results.ts                 # Row dataclass
│   ├── chart/register.ts          # Chart.js registration
│   └── ui.ts                      # DOM helpers
└── routes/
    ├── +layout.svelte             # global layout
    ├── +page.svelte               # dashboard (filters + Chart.js charts)
    ├── corpus/+page.svelte        # configure tasks & corpus
    └── run/+page.svelte           # configure & run a benchmark, streaming progress
```

Everything is **browser-only**: the engine is a client-side `fetch` to the local
OpenAI-compatible server. There is no backend to run.

## Quick start

Start an OpenAI-compatible engine (e.g. Ollama) and pull a model:

```bash
ollama serve
ollama pull llama3
```

Launch the dashboard from the project root:

```bash
pnpm install
pnpm dev
```

The dashboard opens at <http://localhost:5173>. Open it and click **Run** to
benchmark the running engine.

The dashboard sends a JSON body to the engine via `fetch`:

```json
{
  "base_url": "http://localhost:11434",
  "model": "llama3",
  "judge": { "base_url": "http://localhost:11434", "model": "llama3" },
  "task": "my-task-id",
  "timeout": 60,
  "max_concurrent": 1
}
```

The dashboard exposes:

- `/` — dashboard (saved results with filters + Chart.js charts).
- `/run` — configure & run a benchmark, streaming progress.
- `/corpus` — configure tasks and corpus.

## Configuration

Configuration is browser-side. Engines/models/corpus can be loaded from
`IndexedDB` (seeded via the dashboard or `src/lib/storage/`) or entered directly
on the `/run` and `/corpus` pages. See `config.example.yaml` for the shape of an
equivalent configuration file.

| Column                  | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `engine`                | Engine name                                     |
| `model`                 | Model served by the engine                      |
| `judge`                 | Judge name                                      |
| `task_id`               | Task identifier                                 |
| `category`              | Task category                                   |
| `ttft_s`                | Time-to-first-token (seconds)                   |
| `tok_per_s`             | Tokens per second                               |
| `iters_per_s`           | Iterations per second                           |
| `quality_passed`        | Whether the output satisfied all quality checks |
| `quality_deterministic` | Whether deterministic checks passed             |
| `quality_judge`         | Judge score (when a judge is used)              |
| `quality_note`          | Additional judge/quality notes                  |

## Development

```bash
pnpm install          # install dependencies
pnpm dev              # start Vite dev server (http://localhost:5173)
pnpm build            # build the static site to build/
pnpm check            # type-check (svelte-check)
pnpm test             # run the Vitest suite
pnpm lint             # prettier + eslint
```

## License

MIT
