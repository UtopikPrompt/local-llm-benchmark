// Tests for the engine-selection / run orchestration logic.
//
// Mirrors tests/test_controller.py. The TS migration dropped the FastAPI
// controller/services layer; engine selection and the run orchestration now
// live in the lib modules. These tests assert the engine-selection helpers
// (makeEngine) and the run path (runBenchmark) returning rows, adapting the
// Python controller assertions to the TS API.

import { describe, expect, it, vi } from "vitest";

import { makeEngine } from "../lib/engines/index.js";
import { BenchmarkError, NetworkError } from "../lib/errors.js";
import { runBenchmark } from "../lib/runner.js";
import { buildDefaultCorpus } from "../lib/corpus/tasks.js";
import type { EngineConfig } from "../lib/config.js";
import type { BenchmarkConfig } from "../lib/config.js";
import type { Task } from "../lib/corpus/tasks.js";

// A fake engine implementing the Engine interface so runBenchmark type-checks
// without a real client.
class FakeEngine {
  config: EngineConfig;
  name: string;
  model: string;
  base_url: string;
  timeout: number;
  max_concurrent: number;
  constructor(config: EngineConfig) {
    this.config = config;
    this.name = config.name;
    this.model = config.model;
    this.base_url = config.base_url;
    this.timeout = config.timeout;
    this.max_concurrent = config.max_concurrent;
  }
  async *chat(): AsyncGenerator<string> {
    yield "2007";
  }
  list_models() {
    return Promise.resolve([]);
  }
  async close() {}
}

function configWith(engine: EngineConfig, tasks: Task[] = []): BenchmarkConfig {
  const chosen = tasks.length
    ? tasks
    : [buildDefaultCorpus().filter((t) => t.category === "qa")[0]];
  return {
    engines: [engine],
    judges: [],
    tasks: chosen,
    task: null,
    max_concurrent: 1,
    timeout: 60,
    format: "json",
    output: null,
    trials: 3,
  };
}

describe("makeEngine selection", () => {
  it("builds an engine from config", () => {
    const engine = makeEngine({
      name: "ollama",
      base_url: "http://host:11434",
      model: "llama3",
      timeout: 60,
      max_concurrent: 1,
    });
    expect(engine.name).toBe("ollama");
    expect(engine.base_url).toBe("http://host:11434");
  });
});

describe("runBenchmark orchestration", () => {
  it("produces one row per task", async () => {
    const config = configWith({
      name: "ollama",
      base_url: "http://fake",
      model: "llama3",
      timeout: 60,
      max_concurrent: 1,
    });
    const result = await runBenchmark(config);
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0].task_id).toBe("qa-first-iphone-year");
    expect(result.rows[0].engine).toBe("ollama");
  });

  it("reports elapsed time", async () => {
    const config = configWith({
      name: "ollama",
      base_url: "http://fake",
      model: "llama3",
      timeout: 60,
      max_concurrent: 1,
    });
    const result = await runBenchmark(config);
    expect(typeof result.elapsed_s).toBe("number");
    expect(result.elapsed_s).toBeGreaterThanOrEqual(0);
  });
});
