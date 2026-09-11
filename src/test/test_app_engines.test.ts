// Tests that the dashboard can select among multiple configured engines.
//
// Mirrors tests/test_app_engines.py. The TS migration dropped the FastAPI
// `/engines` HTTP endpoint and the app's config-loading path in favour of the
// client-side storage layer, so the tests exercise `loadEngines`/`saveEngines`
// (which persist to IndexedDB) and assert the multi-engine selection + config
// round-trip.

import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EngineConfig } from "../lib/config.js";
import type { BenchmarkConfig } from "../lib/config.js";

// In-memory mock of the IndexedDB persistence so the storage round-trip runs
// under the Node vitest environment.
const enginesStore = new Map<string, Map<number, unknown>>();

vi.mock("../lib/storage/db.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/storage/db.js")>();
  return {
    ...actual,
    put: async (s: string, k: number, v: unknown) => {
      if (!enginesStore.has(s)) enginesStore.set(s, new Map());
      enginesStore.get(s)!.set(k, v);
    },
    get: async (s: string, k: number) => enginesStore.get(s)?.get(k),
    getAll: async (s: string) =>
      Array.from(enginesStore.get(s)?.values() ?? []),
  };
});

import { loadEngines, saveEngines, clearRows } from "../lib/storage/index.js";

function twoEngines(): EngineConfig[] {
  return [
    {
      name: "ollama",
      base_url: "http://host-a:11434",
      model: "llama3",
      timeout: 60,
      max_concurrent: 1,
    },
    {
      name: "ollama-b",
      base_url: "http://host-b:11434",
      model: "llama3.1",
      timeout: 60,
      max_concurrent: 1,
    },
  ];
}

beforeEach(async () => {
  enginesStore.clear();
  await clearRows();
});

describe("loadEngines/saveEngines round-trip", () => {
  it("persists and reloads the configured engines", async () => {
    const engines = twoEngines();
    await saveEngines(engines);
    const reloaded = await loadEngines();
    expect(reloaded).toEqual(engines);
  });

  it("serializes each engine with defaults", async () => {
    const engines = twoEngines();
    await saveEngines(engines);
    const reloaded = await loadEngines();
    expect(reloaded[0]).toEqual({
      name: "ollama",
      base_url: "http://host-a:11434",
      model: "llama3",
      timeout: 60,
      max_concurrent: 1,
    });
  });
});

describe("multi-engine selection", () => {
  it("builds a BenchmarkConfig selecting a configured engine", async () => {
    const engines = twoEngines();
    await saveEngines(engines);
    const loaded = await loadEngines();
    const config: BenchmarkConfig = {
      engines: loaded,
      judges: [],
      tasks: [],
      task: null,
      max_concurrent: 1,
      timeout: 60,
      format: "json",
      output: null,
      trials: 3,
    };
    const selected = config.engines.find((e) => e.name === "ollama-b");
    expect(selected?.base_url).toBe("http://host-b:11434");
    expect(selected?.model).toBe("llama3.1");
    expect(config.engines.find((e) => e.name === "missing")).toBeUndefined();
  });
});
