// Tests for the OpenAI-compatible engine abstraction.
//
// Mirrors tests/test_engines_speed.py. A mocked global `fetch` yields a valid
// SSE stream so the engine must return the tokens in order; `list_models()`
// returns the model ids; `close()` resolves.

import { describe, expect, it, vi } from "vitest";

import { BenchmarkError, NetworkError } from "../lib/errors.js";
import { OpenAICompatEngine } from "../lib/engines/openai_compat.js";
import { makeEngine } from "../lib/engines/index.js";
import type { EngineConfig } from "../lib/config.js";

// Use the web ReadableStream (has static `from`) rather than Node's global
// stream, whose EventEmitter-based type shadows the DOM `from` static.
import { ReadableStream } from "node:stream/web";

const baseConfig: EngineConfig = {
  name: "engine",
  base_url: "http://engine:11434",
  model: "llama3",
  timeout: 30,
  max_concurrent: 1,
};

const encoder = new TextEncoder();

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const token of gen) {
    out.push(token);
  }
  return out;
}

function engine(config: EngineConfig = baseConfig): OpenAICompatEngine {
  return new OpenAICompatEngine(config);
}

async function list(stream = false): Promise<string[]> {
  return collect(engine().chat([], { max_tokens: 1, stream }));
}

function fetchImpl(body: Uint8Array) {
  return async () => ({
    ok: true,
    status: 200,
    statusText: "OK",
    body: ReadableStream.from([body]),
    json: async () => ({}),
  });
}

describe("OpenAICompatEngine.chat (streaming)", () => {
  it("yields streamed tokens in order", async () => {
    // Two SSE frames delivered as two separate chunks to exercise multi-read
    // streaming. Each `data:` line carries a JSON chat-completion message.
    const body = ReadableStream.from([
      encoder.encode(
        `data: ${JSON.stringify({ choices: [{ message: { content: "Hi" } }] })}\n`,
      ),
      encoder.encode(
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

    const tokens = await list(true);
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
            `data: {"choices":[{"message":{"content":null,"reasoning":"the answer"}}]}\n`,
          ),
        ]),
        json: async () => ({}),
      })),
    );

    expect(await list(true)).toEqual(["the answer"]);
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
            `data: {"choices":[{"message":{"content":"a"}}]}\n`,
          ),
          new TextEncoder().encode("data: [DONE]\n"),
        ]),
        json: async () => ({}),
      })),
    );

    expect(await list(true)).toEqual(["a"]);
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

    expect(await list(true)).toEqual(["ok"]);
  });

  it("raises NetworkError on connection failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("boom");
      }),
    );

    await expect(list()).rejects.toBeInstanceOf(NetworkError);
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

    await expect(list()).rejects.toBeInstanceOf(BenchmarkError);
  });

  it("raises BenchmarkError on malformed stream", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: ReadableStream.from([
          new TextEncoder().encode("not json at all"),
        ]),
        json: async () => ({}),
      })),
    );

    await expect(list()).rejects.toBeInstanceOf(BenchmarkError);
  });
});

describe("OpenAICompatEngine.chat (non-streaming)", () => {
  it("returns the full content string", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: undefined,
        json: async () => ({
          choices: [{ message: { content: "answer", reasoning: "none" } }],
        }),
      })),
    );

    expect(await list()).toEqual(["answer"]);
  });

  it("captures reasoning when content is missing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: undefined,
        json: async () => ({
          choices: [{ message: { content: null, reasoning: "reason" } }],
        }),
      })),
    );

    expect(await list()).toEqual(["reason"]);
  });
});

describe("OpenAICompatEngine.list_models", () => {
  it("returns non-empty model ids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        body: undefined,
        json: async () => ({
          data: [{ id: "llama3" }, { id: "" }, { id: "mistral" }],
        }),
      })),
    );

    expect(await engine().list_models()).toEqual(["llama3", "mistral"]);
  });

  it("returns [] for non-200 and on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("boom");
      }),
    );

    expect(await engine().list_models()).toEqual([]);
  });
});

describe("OpenAICompatEngine.close", () => {
  it("resolves without throwing", async () => {
    const e = engine();
    await expect(e.close()).resolves.toBeUndefined();
  });
});

describe("makeEngine", () => {
  it("returns an OpenAICompatEngine", () => {
    const e = makeEngine(baseConfig);
    expect(e).toBeInstanceOf(OpenAICompatEngine);
  });
});
