// Tests for quality scoring.
//
// Mirrors tests/test_quality.py. Quality has two layers: deterministic checks
// (expected substring / validator) and an optional judge model. An answer
// passes if any deterministic check passes OR the judge agrees.

import { describe, expect, it, vi } from "vitest";

import { evaluateQuality } from "../lib/quality.js";
import type { Judge, Task, TaskValidator } from "../lib/corpus/tasks.js";

function task(expected = "2007", validate: TaskValidator | null = null): Task {
  return {
    id: "qa",
    category: "qa",
    prompt: "prompt",
    system: null,
    expected,
    validate,
  };
}

function fakeJudge(
  impl: (
    task: Task,
    answer: string,
  ) => Promise<{ agreed: boolean; note: string }>,
): Judge {
  return {
    name: "judge",
    score: vi.fn(impl),
  } as unknown as Judge;
}

describe("evaluateQuality — deterministic", () => {
  it("passes on expected substring match", async () => {
    const r = await evaluateQuality(
      task("2007"),
      "The first iPhone was in 2007.",
      {
        expected: "2007",
        validate: null,
      },
    );
    expect(r.quality_passed).toBe(true);
    expect(r.quality_deterministic).toBe(true);
    expect(r.quality_judge).toBe(false);
    expect(r.quality_note).toContain("expected substring found");
  });

  it("passes case-insensitively", async () => {
    const r = await evaluateQuality(task("iPhone"), "iPhone released 2007", {
      expected: "iPhone",
      validate: null,
    });
    expect(r.quality_passed).toBe(true);
  });

  it("fails with no match", async () => {
    const r = await evaluateQuality(task("2007"), "nothing here", {
      expected: "2007",
      validate: null,
    });
    expect(r.quality_passed).toBe(false);
    expect(r.quality_deterministic).toBe(false);
  });

  it("passes on validator", async () => {
    const r = await evaluateQuality(
      task("x", (s) => s.trim() === "x = 5"),
      "x = 5",
      {
        expected: "x",
        validate: (s: string) => s.trim() === "x = 5",
      },
    );
    expect(r.quality_passed).toBe(true);
    expect(r.quality_deterministic).toBe(true);
    expect(r.quality_note).toContain("validator passed");
  });
});

describe("evaluateQuality — judge", () => {
  it("judge agrees overrides a negative deterministic result", async () => {
    const judge = {
      name: "judge",
      score: vi.fn(async () => ({ agreed: true, note: "judge agreed" })),
    } as unknown as Judge;
    const r = await evaluateQuality(task("2007"), "whatever", {
      expected: "2007",
      validate: null,
      judge,
    });
    expect(r.quality_passed).toBe(true);
    expect(r.quality_deterministic).toBe(false);
    expect(r.quality_judge).toBe(true);
  });

  it("judge disagrees overrides a positive deterministic result", async () => {
    const judge = {
      name: "judge",
      score: vi.fn(async () => ({ agreed: false, note: "judge said no" })),
    } as unknown as Judge;
    const r = await evaluateQuality(task("2007"), "2007", {
      expected: "2007",
      validate: null,
      judge,
    });
    expect(r.quality_passed).toBe(true);
    expect(r.quality_deterministic).toBe(true);
    expect(r.quality_judge).toBe(false);
    expect(r.quality_note).toContain("judge said no");
  });

  it("judge = undefined means no judge", async () => {
    const r = await evaluateQuality(task(), "answer", {
      expected: null,
      validate: null,
      judge: undefined,
    });
    expect(r.quality_passed).toBe(false);
    expect(r.quality_judge).toBe(false);
  });

  it("composes note from deterministic + judge", async () => {
    const judge = {
      name: "judge",
      score: vi.fn(async () => ({ agreed: false, note: "judge said no" })),
    } as unknown as Judge;
    const r = await evaluateQuality(task("2007"), "2007", {
      expected: "2007",
      validate: null,
      judge,
    });
    expect(r.quality_note).toContain("expected substring found");
    expect(r.quality_note).toContain("judge said no");
  });

  it("records judge failure without throwing", async () => {
    const judge = {
      name: "judge",
      score: vi.fn(async () => {
        throw new Error("boom");
      }),
    } as unknown as Judge;
    const r = await evaluateQuality(task("2007"), "2007", {
      expected: "2007",
      validate: null,
      judge,
    });
    expect(r.quality_passed).toBe(true);
    expect(r.quality_note).toContain("judge failed");
  });
});
