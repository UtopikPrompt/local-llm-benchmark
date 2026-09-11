// Tests for the Judge class.
//
// Mirrors tests/test_runner_judges.py. The Judge wraps an engine and `score`
// runs the judge engine (non-stream) to decide yes/no.

import { describe, expect, it, vi } from "vitest";

import { Judge } from "../lib/engines/judge.js";
import { BenchmarkError } from "../lib/errors.js";
import type { Task } from "../lib/corpus/tasks.js";

function task(prompt = "prompt", expected = "2007"): Task {
  return {
    id: "qa",
    category: "qa",
    prompt,
    system: null,
    expected,
    validate: null,
  };
}

// A fake engine that replays a fixed token string. Implements the full
// `Engine` interface so the `Judge` type-checks without a real client.
class FakeEngine {
  tokens: string[];
  name: string = "fake-judge";
  model: string = "fake";
  base_url: string = "http://fake";
  timeout: number = 30;
  max_concurrent: number = 1;
  constructor(tokens: string[]) {
    this.tokens = tokens;
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

describe("Judge.score", () => {
  it("agrees when the answer contains yes", async () => {
    const judge = new Judge(new FakeEngine(["y", "es"]), "judge");
    const { agreed, note } = await judge.score(task(), "the answer is yes");
    expect(agreed).toBe(true);
    expect(note).toContain("judge agreed");
  });

  it("disagrees when the answer contains no", async () => {
    const judge = new Judge(new FakeEngine(["n", "o"]), "judge");
    const { agreed, note } = await judge.score(task(), "the answer is no");
    expect(agreed).toBe(false);
    expect(note).toContain("judge said no");
  });

  it("handles a system prompt", async () => {
    const judge = new Judge(new FakeEngine(["y", "es"]), "judge");
    const taskWithSystem = task("prompt", "2007");
    (taskWithSystem as Task).system = "You are helpful";
    await judge.score(taskWithSystem, "answer");
    expect(judge.chatMessages[0].role).toBe("system");
    expect(judge.chatMessages[1].role).toBe("user");
    expect(judge.chatMessages[0].content).toContain("grader");
    expect(judge.chatMessages[1].content).toContain("You are helpful");
    expect(judge.chatMessages[1].content).toContain("prompt");
    expect(judge.chatMessages[1].content).toContain("2007");
  });

  it("throws BenchmarkError when the engine fails", async () => {
    const judge = new Judge(new FakeEngine([]), "judge");
    judge.engine.chat = async function* () {
      throw new Error("boom");
    };
    await expect(judge.score(task(), "answer")).rejects.toBeInstanceOf(
      BenchmarkError,
    );
  });
});
