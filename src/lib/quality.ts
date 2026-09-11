// Quality evaluation: deterministic checks plus an optional judge model.
//
// An answer passes if:
//   * a deterministic check matches (expected substring or validator), OR
//   * an optional judge model agrees.
//
// `quality_deterministic` records whether a deterministic check passed;
// `quality_judge` records whether the judge agreed.

import type { Judge, Task, TaskValidator } from "./corpus/tasks.js";
import { BenchmarkError } from "./errors.js";
import type { Row } from "./results.js";

export async function evaluateQuality(
  task: Task,
  answer: string,
  options: {
    expected: string | null;
    validate: TaskValidator | null;
    judge?: Judge;
  },
): Promise<Row> {
  let deterministic = false;
  let note = "";

  if (
    options.expected &&
    answer.toLowerCase().includes(options.expected.toLowerCase())
  ) {
    deterministic = true;
    note = "expected substring found";
  }

  if (options.validate && options.validate(answer)) {
    deterministic = true;
    note = "validator passed";
  }

  let judgeAgreed = false;
  if (options.judge) {
    try {
      const { agreed, note: judgeNote } = await options.judge.score(
        task,
        answer,
      );
      judgeAgreed = agreed;
      note = judgeAgreed ? `${note}; ${judgeNote}` : `${note}; ${judgeNote}`;
    } catch (error) {
      note = `${note}; judge failed: ${error instanceof Error ? error.message : "unknown error"}`;
    }
  }

  const passed = deterministic || judgeAgreed;

  return {
    engine: "",
    model: "",
    judge: options.judge?.name ?? "",
    task_id: task.id,
    category: task.category,
    prompt: task.prompt,
    expected: options.expected ?? "",
    output: answer,
    ttft_s: 0,
    tok_per_s: 0,
    iters_per_s: 0,
    quality_passed: passed,
    quality_deterministic: deterministic,
    quality_judge: judgeAgreed,
    quality_note: note,
  };
}
