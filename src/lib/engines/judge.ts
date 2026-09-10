// Judge: an optional quality-scoring model. `score` runs the judge engine over
// the answer and returns whether it agreed plus a reason.

import { BenchmarkError } from "../errors.js";
import type { Engine, EngineConfig } from "./engines.js";
import type { Task } from "../corpus/tasks.js";
import type { Judge as JudgeConfig } from "../config.js";

const SYSTEM_PROMPT =
  "You are a meticulous grader. Judge whether the model's answer is correct " +
  "based on the task. Reply with exactly 'yes' or 'no' and a one-line reason.";

export class Judge implements import("../tasks.js").Judge {
  engine: Engine;
  name: string;

  constructor(engine: Engine, name: string) {
    this.engine = engine;
    this.name = name;
  }

  async score(
    task: Task,
    answer: string,
  ): Promise<{ agreed: boolean; note: string }> {
    const prompt = task.system
      ? `${task.system}\n\n${task.prompt}`
      : task.prompt;
    const messages = [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content:
          "Task:\n" +
          `${prompt}\n\n` +
          `Expected answer:\n${task.expected ?? ""}\n\n` +
          `Model answer:\n${answer}`,
      },
    ];

    const tokens: string[] = [];
    try {
      for await (const token of this.engine.chat(messages, {
        max_tokens: 64,
        stream: false,
      })) {
        tokens.push(token);
      }
    } catch (error) {
      throw new BenchmarkError("INVALID", "judge failed", error);
    }
    const response = tokens.join("");

    const normalized = response.trim().toLowerCase();
    const agreed = normalized.includes("yes");
    const note = agreed
      ? "judge agreed"
      : `judge said ${normalized || "empty"}`;
    return { agreed, note };
  }
}
