// Tests for the lib service layer (business logic behind the endpoints).
//
// Mirrors tests/test_services.py. The TS migration dropped the server API
// service layer; the business logic now lives in the lib modules. These tests
// exercise the engine-selection and run path directly, asserting the row
// output and the single-engine build.

import { describe, expect, it, vi } from "vitest";

import { DEFAULTS } from "../lib/config.js";
import type { EngineConfig } from "../lib/config.js";
import type { Engine } from "../lib/engines.js";
import { makeEngine } from "../lib/engines/index.js";
import { Judge } from "../lib/engines/judge.js";
import { runBenchmark } from "../lib/runner.js";
import type { BenchmarkConfig } from "../lib/config.js";
import type { Task } from "../lib/corpus/tasks.js";

// A fake engine replaying a fixed token string so the services run without a
// real client. Implements the full Engine interface.
class FakeEngine {
  config: EngineConfig;
  tokens: string[];
  name: string;
  model: string;
  base_url: string;
  timeout: number;
  max_concurrent: number;
  constructor(config: EngineConfig, tokens: string[]) {
    this.config = config;
    this.tokens = tokens;
    this.name = config.name;
    this.model = config.model;
    this.base_url = config.base_url;
    this.timeout = config.timeout;
    this.max_concurrent = config.max_concurrent;
  }
  async *chat(): AsyncGenerator<string> {
    for (const t of this.tokens) {
      yield t;
    }
  }
  list_models() {
    return Promise.resolve([]);
  }
  async close() {}
}

const task: Task = {
  id: "qa-first-iphone-year",
  category: "qa",
  prompt: "What year was the first iPhone released?",
  system: null,
  expected: "2007",
  validate: null,
};

interface Overrides {
  name?: string;
  model?: string;
  base_url?: string;
  max_concurrent?: number;
  timeout?: number;
}

function configWith(
  overrides: Partial<EngineConfig> & Overrides = {},
): BenchmarkConfig {
  const engine: EngineConfig = {
    name: overrides.name ?? "ollama",
    base_url: overrides.base_url ?? "http://x:11434",
    model: overrides.model ?? "m",
    timeout: overrides.timeout ?? DEFAULTS.timeout,
    max_concurrent: overrides.max_concurrent ?? DEFAULTS.max_concurrent,
  };
  return {
    engines: [engine],
    judges: [],
    tasks: [task],
    task: null,
    max_concurrent: DEFAULTS.max_concurrent,
    timeout: DEFAULTS.timeout,
    format: "json",
    output: null,
    trials: 3,
  };
}

// Redirect the engine registry to return our fake engine, deriving the fake
// engine from the config passed by runBenchmark so the row reflects the actual
// engine requested.
vi.mock("../lib/engines/index.js", () => ({
  makeEngine: vi.fn((engine: EngineConfig) => new FakeEngine(engine, ["2007"])),
}));

import { makeEngine as _makeEngine } from "../lib/engines/index.js";

describe("services.run: single engine", () => {
  it("builds a single engine from base_url/model", async () => {
    const result = await runBenchmark(configWith());
    expect(result.rows[0].engine).toBe("ollama");
    expect(result.rows[0].model).toBe("m");
  });
});

describe("services.run: defaults from DEFAULTS", () => {
  it("seeds a single engine from the defaults", async () => {
    const result = await runBenchmark(
      configWith({ name: "ollama", model: DEFAULTS.engine_model }),
    );
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0].engine).toBe("ollama");
    expect(result.rows[0].model).toBe(DEFAULTS.engine_model);
  });
});

describe("Judge scoring service", () => {
  it("scores an answer with a judge engine", async () => {
    const judge = new Judge(
      new FakeEngine(
        {
          name: "judge",
          base_url: "http://fake",
          model: "judge",
          timeout: 30,
          max_concurrent: 1,
        },
        ["y", "es"],
      ) as unknown as Engine,
      "judge",
    );
    const { agreed, note } = await judge.score(task, "the answer is yes");
    expect(agreed).toBe(true);
    expect(note).toContain("judge agreed");
  });
});
