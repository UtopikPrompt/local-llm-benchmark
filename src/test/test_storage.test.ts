// Tests for the storage layer.
//
// Mirrors the Python storage round-trip checks. The low-level IndexedDB
// helpers in `db.ts` are mocked with an in-memory map so the tests run under
// the Node vitest environment.

import { beforeEach, describe, expect, it, vi } from "vitest";

const store = new Map<string, Map<number, unknown>>();

vi.mock("../lib/storage/db.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/storage/db.js")>();
  return {
    ...actual,
    put: async (s: string, k: number, v: unknown) => {
      if (!store.has(s)) store.set(s, new Map());
      store.get(s)!.set(k, v);
    },
    get: async (s: string, k: number) => store.get(s)?.get(k),
    getAll: async (s: string) => Array.from(store.get(s)?.values() ?? []),
  };
});

import {
  loadRows,
  saveRows,
  clearRows,
  loadEngines,
  saveEngines,
  loadModels,
  saveModels,
  loadCorpus,
  saveCorpus,
  exportData,
  importData,
} from "../lib/storage/index.js";
import type { Row } from "../lib/results.js";
import type { EngineConfig } from "../lib/config.js";
import type { Corpus } from "../lib/corpus/tasks.js";

const row: Row = {
  engine: "ollama",
  model: "llama3",
  judge: "llama3",
  task_id: "qa-first-iphone-year",
  category: "qa",
  prompt: "prompt",
  expected: "2007",
  output: "2007",
  ttft_s: 1.2,
  tok_per_s: 99,
  iters_per_s: 10,
  quality_passed: true,
  quality_deterministic: true,
  quality_judge: false,
  quality_note: "",
};

const engine: EngineConfig = {
  name: "ollama",
  base_url: "http://localhost:11434",
  model: "llama3",
  timeout: 60,
  max_concurrent: 1,
};

const corpus: Corpus = {
  tasks: [
    {
      id: "t",
      category: "qa",
      prompt: "p",
      system: null,
      expected: "2007",
      validate: null,
    },
  ],
};

beforeEach(() => {
  for (const map of store.values()) map.clear();
});

describe("row round-trip", () => {
  it("saveRows then loadRows returns the same rows", async () => {
    await saveRows([row]);
    expect(await loadRows()).toEqual([row]);
  });

  it("clearRows removes the stored rows", async () => {
    await saveRows([row]);
    await clearRows();
    expect(await loadRows()).toEqual([]);
  });
});

describe("engine round-trip", () => {
  it("saveEngines then loadEngines returns the same engines", async () => {
    await saveEngines([engine]);
    expect(await loadEngines()).toEqual([engine]);
  });
});

describe("models round-trip", () => {
  it("saveModels then loadModels returns the same models", async () => {
    const models = [{ engine: "ollama", model: "llama3", list: ["a", "b"] }];
    await saveModels(models);
    expect(await loadModels()).toEqual(models);
  });
});

describe("corpus round-trip", () => {
  it("loadCorpus falls back to the default on an empty DB", async () => {
    const c = await loadCorpus();
    expect(c.tasks).toEqual(expect.any(Array));
    expect(c.tasks.length).toBeGreaterThan(0);
  });

  it("saveCorpus then loadCorpus returns the same corpus", async () => {
    await saveCorpus(corpus);
    expect(await loadCorpus()).toEqual(corpus);
  });
});

describe("JSON export / import", () => {
  it("importData then exportData round-trips a full snapshot", async () => {
    await saveRows([row]);
    await saveEngines([engine]);
    await saveModels([{ engine: "ollama", model: "llama3", list: ["a"] }]);
    await saveCorpus(corpus);

    await importData(await exportData());
    expect(await loadRows()).toEqual([row]);
    expect(await loadEngines()).toEqual([engine]);
    expect(await loadModels()).toEqual([
      { engine: "ollama", model: "llama3", list: ["a"] },
    ]);
    expect(await loadCorpus()).toEqual(corpus);
  });

  it("exportData produces a serializable object", async () => {
    await saveRows([row]);
    const data = await exportData();
    const s = JSON.stringify(data);
    expect(typeof s).toBe("string");
    const parsed = JSON.parse(s);
    expect(parsed.rows).toEqual([row]);
  });
});
