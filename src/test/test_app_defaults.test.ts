// Tests that the web UI sources its form defaults from the centralized DEFAULTS.
//
// Mirrors tests/test_app_defaults.py. The TS migration dropped the FastAPI
// `/defaults` HTTP endpoint in favour of SvelteKit, so the dashboard form is
// seeded directly from `DEFAULTS`. This test asserts that the DEFAULTS seed
// values populate a benchmark config the way the run page does, and that the
// config is internally consistent.

import { describe, expect, it } from "vitest";

import { DEFAULTS } from "../lib/config.js";
import type { BenchmarkConfig, EngineConfig } from "../lib/config.js";
import { buildDefaultCorpus } from "../lib/corpus/tasks.js";
import { makeEngine } from "../lib/engines/index.js";

// Replicates the config the run page builds from the form, using DEFAULTS as
// the seed so a fresh page load is populated correctly.
function buildConfigFromDefaults(): BenchmarkConfig {
  const engine: EngineConfig = {
    name: "ollama",
    base_url: DEFAULTS.engine_base_url,
    model: DEFAULTS.engine_model,
    timeout: DEFAULTS.timeout,
    max_concurrent: DEFAULTS.max_concurrent,
  };
  return {
    engines: [engine],
    judges: [],
    tasks: buildDefaultCorpus(),
    task: null,
    max_concurrent: DEFAULTS.max_concurrent,
    timeout: DEFAULTS.timeout,
    format: DEFAULTS.format,
    output: null,
    trials: DEFAULTS.trials,
  };
}

describe("DEFAULTS seed the dashboard form", () => {
  it("produces a valid single-engine config", () => {
    const config = buildConfigFromDefaults();
    expect(config.engines).toHaveLength(1);
    expect(config.engines[0].base_url).toBe(DEFAULTS.engine_base_url);
    expect(config.engines[0].model).toBe(DEFAULTS.engine_model);
    expect(config.engines[0].timeout).toBe(DEFAULTS.timeout);
    expect(config.engines[0].max_concurrent).toBe(DEFAULTS.max_concurrent);
  });

  it("seeds the default corpus for the selected category", () => {
    const config = buildConfigFromDefaults();
    expect(config.tasks).toHaveLength(8);
    // The default corpus opens with a "doc" task.
    expect(config.tasks[0].category).toBe("doc");
  });

  it("constructs a runnable engine from the defaults", () => {
    const config = buildConfigFromDefaults();
    const engine = makeEngine(config.engines[0]);
    expect(engine.name).toBe(config.engines[0].name);
    expect(engine.base_url).toBe(DEFAULTS.engine_base_url);
  });

  it("uses the default trials", () => {
    const config = buildConfigFromDefaults();
    expect(config.trials).toBe(DEFAULTS.trials);
  });
});
