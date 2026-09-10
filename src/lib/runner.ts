// Benchmark orchestrator: run the full benchmark against a config and return
// one Row per (engine, task) trial.
//
// For every engine, every selected task is benchmarked for speed. The fastest
// trial is then quality-scored (deterministic checks + optional judge).

import { BenchmarkError } from './errors.js';
import { benchmarkSpeed } from './benchmark.js';
import { evaluateQuality } from './quality.js';
import { makeEngine } from './engines/index.js';
import { Judge } from './engines/judge.js';
import type { BenchmarkConfig, EngineConfig, JudgeConfig } from './config.js';
import type { Row } from './results.js';
import type { Task, TaskValidator } from './tasks.js';

export interface RunResult {
	rows: Row[];
	elapsed_s: number;
}

function emptyRow(engine: EngineConfig, task: Task, prompt: string): Row {
	return {
		engine: engine.name,
		model: engine.model,
		judge: '',
		task_id: task.id,
		category: task.category,
		prompt,
		expected: task.expected ?? '',
		output: '',
		ttft_s: 0,
		tok_per_s: 0,
		iters_per_s: 0,
		quality_passed: false,
		quality_deterministic: false,
		quality_judge: false,
		quality_note: 'no speed rows produced',
	};
}

export async function runBenchmark(config: BenchmarkConfig): Promise<RunResult> {
	const start = performance.now();
	const rows: Row[] = [];

	for (const engine of config.engines) {
		const engineInstance = makeEngine(engine);
		for (const task of config.tasks) {
			try {
				const speedRows = await benchmarkSpeed(engineInstance, task, {
					max_tokens: 64,
					trials: config.trials,
					max_concurrent: config.max_concurrent,
				});

				if (!speedRows.length) {
					rows.push(emptyRow(engine, task, task.prompt));
					continue;
				}

				const best = speedRows.reduce(
					(a, b) => (a.tok_per_s >= b.tok_per_s ? a : b),
					speedRows[0]
				);

				const quality = await evaluateQuality(task, best.output, {
					expected: task.expected,
					validate: task.validate,
					judge: config.judges.length ? new Judge(makeEngine(config.judges[0]), config.judges[0].name) : undefined,
				});
				best.judge = quality.judge;
				best.quality_passed = quality.quality_passed;
				best.quality_deterministic = quality.quality_deterministic;
				best.quality_judge = quality.quality_judge;
				best.quality_note = quality.quality_note;
				rows.push(best);
			} catch (error) {
				rows.push(emptyRow(engine, task, task.prompt));
			}
		}
	}

	return { rows, elapsed_s: (performance.now() - start) / 1000 };
}
