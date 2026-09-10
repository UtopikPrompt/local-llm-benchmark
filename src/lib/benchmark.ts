// Speed benchmark: measure streaming throughput of an engine.
//
// For each task measures:
//   * TTFT — time-to-first-token (wall-clock from request to first token).
//   * tok/s — tokens generated / total elapsed.
//   * iters/s — trials / total elapsed.
//
// Requests are throttled with a semaphore of size `max_concurrent`.

import { BenchmarkError } from "./errors.js";
import { Semaphore } from "./util.js";
import type { Engine, EngineConfig } from "./engines.js";
import type { Row } from "./results.js";

interface Trial {
  tokens: number;
  ttft_s: number;
  tok_per_s: number;
  iters_per_s: number;
}

async function streamTokens(
  engine: Engine,
  messages: Array<{ role: string; content: string }>,
  max_tokens: number,
): Promise<{ tokens: number; ttft_s: number }> {
  const tokens: string[] = [];
  let ttft_s = 0;
  const first = performance.now();
  let count = 0;

  const tokenStream = engine.chat(messages, { max_tokens, stream: true });
  try {
    for await (const token of tokenStream) {
      count += 1;
      tokens.push(token);
      if (count === 1) {
        ttft_s = (performance.now() - first) / 1000;
      }
    }
  } catch (error) {
    throw new BenchmarkError("INVALID", "streaming failed", error);
  }

  return { tokens: count, ttft_s };
}

export async function benchmarkSpeed(
  engine: Engine,
  task: { id: string; category: string; prompt: string; system?: string },
  options: { max_tokens: number; trials: number; max_concurrent: number },
): Promise<Row[]> {
  const system = task.system ?? "";
  const messages: Array<{ role: string; content: string }> = [];
  if (system) {
    messages.push({ role: "system", content: system });
  }
  messages.push({ role: "user", content: task.prompt });

  const start = performance.now();
  const results: Trial[] = [];

  const semaphore = new Semaphore(options.max_concurrent);
  for (let trial = 0; trial < options.trials; trial += 1) {
    const trialStart = performance.now();
    await semaphore.withAcquired(async () => {
      const { tokens, ttft_s } = await streamTokens(
        engine,
        messages,
        options.max_tokens,
      );
      const elapsed = (performance.now() - trialStart) / 1000;
      results.push({
        tokens,
        ttft_s,
        tok_per_s: tokens / elapsed,
        iters_per_s: 1 / elapsed,
      });
    });
  }

  const totalElapsed = (performance.now() - start) / 1000;
  return results.map((trial) => ({
    engine: engine.name,
    model: engine.model,
    judge: "",
    task_id: task.id,
    category: task.category,
    prompt: task.prompt,
    expected: "",
    output: "",
    ttft_s: trial.ttft_s,
    tok_per_s: trial.tok_per_s,
    iters_per_s: options.trials / totalElapsed,
    quality_passed: false,
    quality_deterministic: false,
    quality_judge: false,
    quality_note: "",
  }));
}
