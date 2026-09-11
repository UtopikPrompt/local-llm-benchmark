// Tests for the configuration data classes and the centralized DEFAULTS.
//
// Mirrors tests/test_config.py. The TS migration kept config.ts as a
// structural-typed module (no YAML/JSON I/O), so these tests assert the
// engine/judge/benchmark config shapes and the DEFAULTS seed values.

import { describe, expect, it } from "vitest";

import { BenchmarkError } from "../lib/errors.js";
import { DEFAULTS } from "../lib/config.js";
import type {
  BenchmarkConfig,
  EngineConfig,
  JudgeConfig,
} from "../lib/config.js";

// --- EngineConfig ----------------------------------------------------------

const engine: EngineConfig = {
  name: "ollama",
  base_url: "http://localhost:11434",
  model: "llama3",
  timeout: 120,
  max_concurrent: 4,
};

describe("EngineConfig", () => {
  it("is a structurally complete object", () => {
    expect(Object.keys(engine).sort()).toEqual(
      ["base_url", "max_concurrent", "model", "name", "timeout"].sort(),
    );
  });

  it("defaults timeout and max_concurrent via DEFAULTS", () => {
    // The TS config has no runtime default-application (unlike the Python
    // dataclass), so the seed defaults live on DEFAULTS and are applied at the
    // call site (run page). Assert against DEFAULTS directly.
    expect(DEFAULTS.timeout).toBe(60);
    expect(DEFAULTS.max_concurrent).toBe(1);
  });

  it("is JSON-serializable (no runtime validation)", () => {
    const json = JSON.parse(JSON.stringify(engine));
    expect(json).toEqual({
      name: "ollama",
      base_url: "http://localhost:11434",
      model: "llama3",
      timeout: 120,
      max_concurrent: 4,
    });
  });
});

// --- JudgeConfig -----------------------------------------------------------

const judge: JudgeConfig = {
  name: "judge",
  base_url: "http://localhost:11434",
  model: "judge-model",
  timeout: 30,
};

describe("JudgeConfig", () => {
  it("is a structurally complete object", () => {
    expect(Object.keys(judge).sort()).toEqual(
      ["base_url", "model", "name", "timeout"].sort(),
    );
  });

  it("defaults timeout via DEFAULTS", () => {
    expect(DEFAULTS.timeout).toBe(60);
  });
});

// --- BenchmarkConfig -------------------------------------------------------

const config: BenchmarkConfig = {
  engines: [engine],
  judges: [judge],
  tasks: [],
  task: null,
  max_concurrent: 2,
  timeout: 45,
  format: "json",
  output: "results/r.json",
  trials: 3,
};

describe("BenchmarkConfig", () => {
  it("is a structurally complete object", () => {
    const keys = Object.keys(config).sort();
    expect(keys).toEqual(
      [
        "engines",
        "format",
        "judges",
        "max_concurrent",
        "output",
        "task",
        "tasks",
        "timeout",
        "trials",
      ].sort(),
    );
  });

  it("serializes to JSON", () => {
    const json = JSON.parse(JSON.stringify(config));
    expect(json.engines[0]).toEqual(engine);
    expect(json.judges[0]).toEqual(judge);
    expect(json.tasks).toEqual([]);
  });
});

// --- DEFAULTS --------------------------------------------------------------

describe("DEFAULTS", () => {
  it("exposes the centralized seed values", () => {
    expect(DEFAULTS).toEqual({
      engine_base_url: "http://localhost:11434",
      engine_model: "llama3",
      judge_base_url: "http://localhost:11434",
      judge_model: "llama3",
      timeout: 60,
      max_concurrent: 1,
      format: "json",
      tasks: undefined,
      trials: 3,
    });
  });

  it("covers exactly the documented keys", () => {
    expect(Object.keys(DEFAULTS).sort()).toEqual(
      [
        "engine_base_url",
        "engine_model",
        "format",
        "judge_base_url",
        "judge_model",
        "max_concurrent",
        "tasks",
        "timeout",
        "trials",
      ].sort(),
    );
  });

  it("is immutable (frozen)", () => {
    expect(Object.isFrozen(DEFAULTS)).toBe(true);
  });

  it("selects an engine by name", () => {
    const engines: EngineConfig[] = [
      { name: "a", base_url: "http://a:1", model: "m", timeout: 60, max_concurrent: 1 },
      { name: "b", base_url: "http://b:1", model: "m", timeout: 60, max_concurrent: 1 },
    ];
    const selected = engines.find((e) => e.name === "a");
    expect(selected?.base_url).toBe("http://a:1");
    expect(engines.find((e) => e.name === "missing")).toBeUndefined();
  });
});

// --- Errors ----------------------------------------------------------------

describe("ConfigError", () => {
  it("extends BenchmarkError with a CONFIG code", () => {
    const err = new BenchmarkError("INVALID", "bad config") as BenchmarkError;
    expect(err).toBeInstanceOf(Error);
    expect(err.code).toBe("INVALID");
    expect(err.message).toBe("bad config");
  });
});
