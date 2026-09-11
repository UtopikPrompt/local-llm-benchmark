// Tests for the task corpus: :type:`Task`, :type:`Category`,
// :func:`buildDefaultCorpus`, and the deterministic validators.
//
// Mirrors tests/test_corpus.py. The TS migration dropped load_tasks/task_by_id
// (YAML/JSON disk I/O) in favour of buildDefaultCorpus, so these tests assert
// the corpus shape, the four categories, and the math validators.

import { describe, expect, it } from "vitest";

import {
  buildDefaultCorpus,
  CATEGORIES,
  validateArea,
  validateSolution,
} from "../lib/corpus/tasks.js";
import type { Category, Task } from "../lib/corpus/tasks.js";

// --- Category --------------------------------------------------------------

describe("Category", () => {
  it("has the four documented categories", () => {
    expect(CATEGORIES).toEqual(["doc", "code", "qa", "math"]);
  });

  it("is a string union of primitives", () => {
    const literal = "math" as Category;
    expect(typeof literal).toBe("string");
  });

  it("validates each category", () => {
    for (const c of CATEGORIES) {
      expect(CATEGORIES.includes(c)).toBe(true);
    }
  });
});

// --- Task ------------------------------------------------------------------

describe("Task", () => {
  it("has the required fields", () => {
    const task = buildDefaultCorpus()[0];
    expect(Object.keys(task).sort()).toEqual(
      ["category", "expected", "id", "prompt", "system", "validate"].sort(),
    );
  });

  it("defaults system and validate to null", () => {
    const task: Task = {
      id: "qa",
      category: "qa",
      prompt: "p",
      system: null,
      expected: "2007",
      validate: null,
    };
    expect(task.system).toBeNull();
    expect(task.validate).toBeNull();
  });

  it("covers all categories", () => {
    const corpus = buildDefaultCorpus();
    const categories = new Set(corpus.map((t) => t.category));
    expect(categories.size).toBe(4);
    for (const c of CATEGORIES) {
      expect(categories.has(c)).toBe(true);
    }
  });
});

// --- buildDefaultCorpus ----------------------------------------------------

describe("buildDefaultCorpus", () => {
  it("returns all four canonical task ids", () => {
    const ids = new Set(buildDefaultCorpus().map((t) => t.id));
    expect(ids.has("doc-rest-api")).toBe(true);
    expect(ids.has("code-httpx-get-timeout")).toBe(true);
    expect(ids.has("qa-first-iphone-year")).toBe(true);
    expect(ids.has("math-solve-2x-5-15")).toBe(true);
  });

  it("returns exactly 8 tasks", () => {
    expect(buildDefaultCorpus()).toHaveLength(8);
  });

  it("attaches validators to the math tasks", () => {
    const corpus = buildDefaultCorpus();
    const math = corpus.find((t) => t.id === "math-solve-2x-5-15");
    expect(math?.validate).not.toBeNull();
    if (!math?.validate) return;
    expect(math.validate!("x = 5")).toBe(true);
  });

  it("does not mutate the shared default", () => {
    const corpus = buildDefaultCorpus();
    corpus[0].id = "mutated";
    expect(buildDefaultCorpus()[0].id).toBe("doc-rest-api");
  });
});

// --- Validators ------------------------------------------------------------

describe("validateSolution", () => {
  it("accepts x = 5 and x=5", () => {
    expect(validateSolution("x = 5")).toBe(true);
    expect(validateSolution("x=5")).toBe(true);
  });

  it("rejects other solutions", () => {
    expect(validateSolution("x = 6")).toBe(false);
  });
});

describe("validateArea", () => {
  it("accepts the correct area within tolerance", () => {
    expect(validateArea("153.938")).toBe(true);
  });

  it("rejects non-numeric input", () => {
    expect(validateArea("not-a-number")).toBe(false);
  });
});
