// Tests for the OpenAI-compatible engine backend and the speed benchmark.
//
// Mirrors tests/test_engines_speed.py. The TS migration replaced the httpx
// transport with the global `fetch`, so these tests stub `fetch` to yield SSE
// streams / JSON payloads and assert the engine parses them correctly.

import { describe, expect, it, vi } from "vitest";
import { benchmarkSpeed } from "../lib/benchmark.js";
import { BenchmarkError, NetworkError } from "../lib/errors.js";
import { OpenAICompatEngine } from "../lib/engines/openai_compat.js";
import { Judge } from "../lib/engines/judge.js";
import { evaluateQuality } from "../lib/quality.js";
import { makeEngine } from "../lib/engines/index.js";
import { buildDefaultCorpus } from "../lib/corpus/tasks.js";
import { type Task } from "../lib/corpus/tasks.js";
import type { EngineConfig } from "../lib/config.js";
import type { Row } from "../lib/results.js";

import { ReadableStream } from "node:stream/web";

const baseConfig: EngineConfig = {
  name: "engine",
  base_url: "http://engine:11434",
  model: "llama3",
  timeout: 30,
  max_concurrent: 1,
};

const corpus = buildDefaultCorpus();
const task: Task = corpus[0];

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const token of gen) {
    out.push(token);
  }
  return out;
}

function engine(): OpenAICompatEngine {
  return new OpenAICompatEngine(baseConfig);
}

// --- chat streaming --------------------------------------------------------

describe("OpenAICompatEngine.chat (streaming)", () => {
  it("yields streamed tokens in order", async () => {
    const body = ReadableStream.from([
      new TextEncoder().encode(
        `data: ${JSON.stringify({ choices: [{ message: { content: "Hi" } }] })}\n`,
      ),
      new TextEncoder().encode(
        `data: ${JSON.stringify({ choices: [{ message: { content: "there" } }] })}\n`,
      ),
    ]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body,
      })),
    );

    const tokens = await collect(
      engine().chat([], { max_tokens: 10, stream: true }),
    );
    expect(tokens).toEqual(["Hi", "there"]);
  });

  it("captures the reasoning field when content is absent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: ReadableStream.from([
          new TextEncoder().encode(
            `data: ${JSON.stringify({ choices: [{ message: { content: null, reasoning: "the answer" } }] })}\n`,
          ),
        ]),
        json: async () => ({}),
      })),
    );

    expect(
      await collect(engine().chat([], { max_tokens: 10, stream: true })),
    ).toEqual(["the answer"]);
  });

  it("skips data: [DONE]", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: ReadableStream.from([
          new TextEncoder().encode(
            `data: ${JSON.stringify({ choices: [{ message: { content: "a" } }] })}\n`,
          ),
          new TextEncoder().encode("data: [DONE]\n"),
        ]),
        json: async () => ({}),
      })),
    );

    expect(
      await collect(engine().chat([], { max_tokens: 10, stream: true })),
    ).toEqual(["a"]);
  });

  it("ignores malformed SSE lines", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: ReadableStream.from([
          new TextEncoder().encode("not an sse line\n"),
          new TextEncoder().encode(`data: ${JSON.stringify({ foo: "bar" })}\n`),
          new TextEncoder().encode(
            `data: ${JSON.stringify({ choices: [{ message: { content: "ok" } }] })}\n`,
          ),
        ]),
        json: async () => ({}),
      })),
    );

    expect(
      await collect(engine().chat([], { max_tokens: 10, stream: true })),
    ).toEqual(["ok"]);
  });

  it("raises NetworkError on connection failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("boom");
      }),
    );

    await expect(
      collect(engine().chat([], { max_tokens: 10, stream: false })),
    ).rejects.toBeInstanceOf(NetworkError);
  });

  it("raises BenchmarkError on HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 500,
        statusText: "Server Error",
        body: undefined,
        json: async () => ({}),
      })),
    );

    await expect(
      collect(engine().chat([], { max_tokens: 10, stream: false })),
    ).rejects.toBeInstanceOf(BenchmarkError);
  });
});

// --- list_models -----------------------------------------------------------

describe("OpenAICompatEngine.list_models", () => {
  it("returns non-empty model ids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: ReadableStream.from([
          new TextEncoder().encode(
            JSON.stringify({
              data: [{ id: "llama3" }, { id: "" }, { id: "mistral" }],
            }),
          ),
        ]),
        json: async () => ({
          data: [{ id: "llama3" }, { id: "" }, { id: "mistral" }],
        }),
      })),
    );

    const models = await engine().list_models();
    expect(models).toEqual(["llama3", "mistral"]);
  });

  it("returns an empty list on a missing endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 404,
        statusText: "Not Found",
        body: undefined,
        json: async () => ({}),
      })),
    );

    expect(await engine().list_models()).toEqual([]);
  });
});

// --- benchmarkSpeed --------------------------------------------------------

describe("benchmarkSpeed", () => {
  it("produces one row per trial with throughput", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: ReadableStream.from([
          new TextEncoder().encode(
            `data: ${JSON.stringify({ choices: [{ message: { content: "a" } }] })}\n`,
          ),
        ]),
        json: async () => ({}),
      })),
    );

    const rows = await benchmarkSpeed(engine(), task, {
      max_tokens: 8,
      trials: 3,
      max_concurrent: 1,
    });

    expect(rows).toHaveLength(3);
    for (const row of rows) {
      expect(row.engine).toBe("engine");
      expect(row.task_id).toBe(task.id);
      expect(row.tok_per_s).toBeGreaterThan(0);
    }
  });

  it("degrades gracefully on a downstream error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 500,
        statusText: "Server Error",
        body: undefined,
        json: async () => ({}),
      })),
    );

    await expect(
      benchmarkSpeed(engine(), task, {
        max_tokens: 8,
        trials: 2,
        max_concurrent: 1,
      }),
    ).rejects.toBeInstanceOf(BenchmarkError);
  });
});

// --- evaluateQuality -------------------------------------------------------

describe("evaluateQuality", () => {
  it("passes deterministically on an expected substring", async () => {
    const row = await evaluateQuality(task, "the answer is 2007", {
      expected: "2007",
      validate: task.validate,
    });
    expect(row.quality_passed).toBe(true);
    expect(row.quality_deterministic).toBe(true);
    expect(row.quality_judge).toBe(false);
  });

  it("passes when the judge agrees", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: undefined,
        json: async () => ({
          choices: [{ message: { content: "yes" }, finish_reason: "stop" }],
        }),
      })),
    );

    const judge = new Judge(makeEngine(baseConfig), "judge");
    const row = await evaluateQuality(task, "a wrong answer", {
      expected: "2007",
      validate: task.validate,
      judge,
    });
    expect(row.quality_judge).toBe(true);
  });
});
