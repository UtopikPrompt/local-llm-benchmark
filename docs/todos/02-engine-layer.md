# Sub-prompt 2/7 — Engine layer

Rebuild the OpenAI-compatible engine abstraction in TypeScript so it can stream
chat completions from Ollama / LM Studio and expose everything the runner and
judge need. This is the networking core.

## Context

`src/lib/engines/` already has skeleton files (`engines.ts`, `index.ts`,
`judge.ts`, `models.ts`, `openai_compat.ts`). The reference Python lives in
`local_llm_benchmark/engines/{base.py, openai_compat.py}`. Port to TS.

## Goals

- **`src/lib/engines/engines.ts`** — the `Engine` interface:
  - `config: EngineConfig`.
  - `chat(messages, options)` — an `AsyncGenerator<string>` yielding one token
    at a time. `options = { max_tokens, stream }`.
  - `list_models(): Promise<string[]>`.
  - `close(): Promise<void>` (release network resources).
    Resolve where `EngineConfig` lives so the UI import (`EngineConfig`) works —
    the engine owns the engine's config, but `config.ts` already defines one.
    Decide the single source and export it consistently.
- **`src/lib/engines/openai_compat.ts`** — `OpenAICompatEngine implements Engine`:
  - Streaming via `fetch` + `ReadableStream` reader; parse SSE
    (`data: <json>`), extract `choices[0].message.content` (fallback
    `.reasoning`), skip `data: [DONE]`. Yield each content chunk as a token.
  - Non-stream path returns the single full content string.
  - On HTTP error → `NetworkError`; on malformed stream → `BenchmarkError`.
  - `list_models()` → `GET /v1/models`, return non-empty `id`s.
- **`src/lib/engines/judge.ts`** — `Judge` class wrapping an engine:
  - `constructor(engine, name)`.
  - `score(task, answer): Promise<{ agreed, note }>` — build a grader prompt,
    run the judge engine (non-stream), decide `"yes"`/`"no"`, return
    `{agreed, note}`.
- **`src/lib/engines/models.ts`** — helper `listModels(engine)`.
- **`src/lib/engines/index.ts`** — `makeEngine(config): Engine`.

## Known traps

- **Naming mismatch:** the UI passes `max_concurrent`, but the engine
  convention uses `maxConcurrent`. Standardize on `max_concurrent` everywhere
  (the spec and ADR both say `max_concurrent`).
- `EngineConfig` is duplicated between `config.ts` and `engines.ts`. Keep one
  definition and re-export/import the other — do not let two definitions exist.
- The `Semaphore` in `src/lib/util.ts` throttles concurrency by `max_concurrent`;
  the engine must `close()` so the runner can release it in `finally`.

## Acceptance criteria

- A mocked `fetch` yields a valid SSE stream and the engine returns the tokens
  in order; `list_models()` returns the model ids.
- `makeEngine()` returns an `OpenAICompatEngine`.
- `pnpm check` clean for these files.

## Dependency

Imports from #1 (`config.ts`, `corpus/tasks.ts`, `errors.ts`).

## Status

**State:** Complete — `engines.ts`, `openai_compat.ts`, `judge.ts`, `models.ts`, `index.ts` all implemented. `Judge` type mismatch and the `EngineConfig` re-export concern are resolved: `Judge` exposes `name`/`model`, `EngineConfig` is defined once and re-exported consistently, and `pnpm check` reports **0 errors**. Standardized on `max_concurrent` (snake_case) everywhere. Verified by tests (`src/test/test_engines.test.ts`: mocked SSE stream yields tokens in order, `list_models()` returns ids, `close()` resolves, `makeEngine()` returns `OpenAICompatEngine`).

**Goals:**

- [x] `src/lib/engines/engines.ts` — `Engine` interface (`chat`, `list_models`, `close`)
- [x] `src/lib/engines/openai_compat.ts` — `OpenAICompatEngine` (SSE streaming, `list_models`)
- [x] `src/lib/engines/judge.ts` — `Judge` class (`score`)
- [x] `src/lib/engines/models.ts` — `listModels()` helper
- [x] `src/lib/engines/index.ts` — `makeEngine()`

**Notes:**

- Standardized on `max_concurrent` (snake_case) everywhere; single `EngineConfig` definition.
