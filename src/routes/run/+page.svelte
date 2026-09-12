<script lang="ts">
	import { onMount } from 'svelte';
	import { BenchmarkError } from '$lib/errors.js';
	import { DEFAULTS } from '$lib/config.js';
	import { loadEngines, loadTasks, saveEngines, saveTasks } from '$lib/storage/index.js';
	import { makeEngine } from '$lib/engines/index.js';
	import { buildDefaultCorpus } from '$lib/corpus/tasks.js';

import type { EngineConfig, JudgeConfig } from '$lib/config.js';
import type { BenchmarkConfig } from '$lib/config.js';
import type { Row } from '$lib/results.js';
import type { Category, Task } from '$lib/corpus/tasks.js';

let engines: EngineConfig[] = [];
	// Autosave: debounced write to IndexedDB on any field change, so no
	// Save button is required.
	let ready = true;
	let savedSignature = '';
	let saveTimer = 0;

	onMount(async () => {
		engines = await loadEngines();
		taskIds = (await loadTasks()).map((t) => t.id).join('\n');
		savedSignature = currentSignature();
	});

	function currentSignature(): string {
		return [
			engineName,
			engineBaseUrl,
			engineModel,
			judgeName,
			judgeBaseUrl,
			judgeModel,
			taskCategory,
			taskSystems,
			taskIds,
			taskExpected,
			trials,
			max_concurrent,
			timeout,
			useJudge,
		].join('\u0000');
	}

	$: {
		if (ready && typeof document !== 'undefined') {
			if (savedSignature !== currentSignature()) {
				console.log('[DEBUG] save triggered', currentSignature().slice(0, 50));
				savedSignature = currentSignature();
				clearTimeout(saveTimer);
				saveTimer = setTimeout(async () => {
					await persistConfig();
				}, 400);
			}
		}
	}

let lastFetchUrl = '';

$: if (ready && engineBaseUrl) {
		if (lastFetchUrl !== engineBaseUrl) {
			// Reactive statements can't be async; defer the fetch so the
			// await runs outside the reactive context. This only re-runs when
			// the Base URL (or initial mount) changes.
			lastFetchUrl = engineBaseUrl;
			setTimeout(fetchModels, 0);
		}
	}

	async function fetchModels(): Promise<void> {
		loadingModels = true;
		modelsError = '';
		modelOptions = [];
		try {
			const engine = makeEngine({
				name: engineName,
				base_url: engineBaseUrl,
				model: engineModel,
				timeout,
				max_concurrent,
			});
			const models = await engine.list_models();
			// Deduplicate; keep order (first occurrence wins).
			const seen = new Set<string>();
			for (const id of models) {
				if (!seen.has(id)) {
					seen.add(id);
					modelOptions.push({ id, label: id || engineBaseUrl });
				}
			}
			if (!modelOptions.some((m) => m.id === engineModel)) {
				modelOptions.push({ id: engineModel, label: engineModel });
			}
		} catch (error) {
			modelsError = error instanceof BenchmarkError
				? error.message
				: String(error);
		} finally {
			// `loadingModels` is not read by the reactive guard (that reads
			// `lastFetchUrl`), so this does not re-trigger the fetch.
			loadingModels = false;
		}
	}

	let engineName = DEFAULTS.engine_base_url;
	let engineBaseUrl = DEFAULTS.engine_base_url;
	let engineModel = DEFAULTS.engine_model;
	let modelOptions: Array<{ id: string; label: string }> = [];
	let loadingModels = false;

	let modelsError = '';
	let judgeName = DEFAULTS.judge_base_url;
	let judgeBaseUrl = DEFAULTS.judge_base_url;
	let judgeModel = DEFAULTS.judge_model;
	// 'all' is a UI selection, not a real category; resolved in buildTasks().
	let taskCategory: string = 'all';
	let taskSystems = '';
	let taskIds = '';
	let taskExpected = '';
	let trials = DEFAULTS.trials;
	let max_concurrent = DEFAULTS.max_concurrent;
	let timeout = DEFAULTS.timeout;
	let useJudge = false;

	let running = false;
	let status = '';
	let rows: Row[] = [];
	let errors: BenchmarkError[] = [];

async function persistConfig(): Promise<void> {
		await buildTasks();
		const config: BenchmarkConfig = {
			engines: [
				{
					name: engineName,
					base_url: engineBaseUrl,
					model: engineModel,
					timeout,
					max_concurrent,
				},
			],
			judges: useJudge
				? [
					{
						name: judgeName,
						base_url: judgeBaseUrl,
						model: judgeModel,
						timeout,
					},
				]
				: [],
			max_concurrent,
			timeout,
			trials,
			tasks: buildTasks(),
			task: null,
			format: DEFAULTS.format,
			output: null,
		};
		await Promise.all([
			saveEngines(config.engines),
			saveJudges(config.judges),
			saveModels(config.models),
			saveTasks(buildTasks()),
		]);
	}

	function buildTasks(): Task[] {
		const systems = taskSystems.split('\n').map((s) => s.trim()).filter(Boolean);
		const expected = taskExpected.split('\n').map((s) => s.trim()).filter(Boolean);
		return taskIds
			.split('\n')
			.map((id) => id.trim())
			.filter(Boolean)
			.map((id, index) => {
				const category: Category =
					taskCategory === 'all'
						? 'qa'
						: (taskCategory as Category);
				return {
					id,
					category,
					prompt: id,
					system: systems[index] ?? null,
					expected: expected[index] ?? null,
					validate: null,
				};
			});
	}

	async function runBenchmark(): Promise<void> {
		running = true;
		status = 'running';
		rows = [];
		errors = [];
		try {
			const { runBenchmark: runner } = await import('$lib/runner.js');
			const config: BenchmarkConfig = {
				engines: [
					{
						name: engineName,
						base_url: engineBaseUrl,
						model: engineModel,
						timeout,
						max_concurrent,
					},
				],
				judges: useJudge
					? [
							{
								name: judgeName,
								base_url: judgeBaseUrl,
								model: judgeModel,
								timeout,
							},
						]
					: [],
				max_concurrent,
				timeout,
				trials,
				tasks: buildTasks(),
				task: null,
				format: DEFAULTS.format,
				output: null,
			};
			const result = await runner(config);
			rows = result.rows;
			status = `done: ${rows.length} rows in ${result.elapsed_s.toFixed(2)}s`;
		} catch (error) {
			errors.push(error instanceof BenchmarkError ? error : new BenchmarkError('INVALID', String(error)));
			status = 'error';
		}
	}
</script>
	<div class="page-header">
		<h1>Run benchmark</h1>
		<p class="subtitle">Configure the engine under test, then run the benchmark against the corpus.</p>
	</div>

<div class="card">
	<h2 class="panel-title">Engine</h2>
	<div class="field">
			<label>Engine name
				<input bind:value={engineName} placeholder="Ollama" />
			</label>
	</div>
	<div class="field">
			<label>Base URL
				<input bind:value={engineBaseUrl} placeholder="http://localhost:11434" />
			</label>
	</div>
	<div class="field">
			<label>Model
				{#if loadingModels}
					<span class="spinner">Loading models&hellip;</span>
				{:else if modelsError}
					<span class="error">{modelsError}</span>
				{/if}
				<select bind:value={engineModel}>
					<option value="" disabled>Select model</option>
					{#each modelOptions as option}
						<option value={option.id}>{option.label}</option>
					{/each}
				</select>
			</label>
	</div>
</div>

<div class="card">
	<h2 class="panel-title">Judge (optional)</h2>
	<div class="field">
		<label class="checkbox">
			<input type="checkbox" bind:checked={useJudge} />
			<span>Use a judge model to score quality</span>
		</label>
	</div>
	{#if useJudge}
		<div class="field">
			<label>Judge name
				<input bind:value={judgeName} placeholder="judge" />
			</label>
		</div>
		<div class="field">
			<label>Judge base URL
				<input bind:value={judgeBaseUrl} placeholder="http://localhost:11434" />
			</label>
		</div>
		<div class="field">
			<label>Judge model
				<input bind:value={judgeModel} placeholder="gamma4:e4b" />
			</label>
		</div>
	{/if}
</div>

<div class="card">
	<h2 class="panel-title">Tasks</h2>
	<div class="field">
			<label>Category
				<select bind:value={taskCategory}>
					<option value="all">all</option>
					<option value="doc">doc</option>
					<option value="code">code</option>
					<option value="qa">qa</option>
					<option value="math">math</option>
				</select>
			</label>
	</div>
	<div class="field">
		<label>Task IDs (one per line)
			<textarea bind:value={taskIds} placeholder="doc-rest-api" rows="6"></textarea>
		</label>
	</div>
	<div class="field">
		<label>Systems (one per line)
			<textarea bind:value={taskSystems} rows="3"></textarea>
		</label>
	</div>
	<div class="field">
		<label>Expected answers (one per line)
			<textarea bind:value={taskExpected} rows="3"></textarea>
		</label>
	</div>
</div>

<div class="card">
	<h2 class="panel-title">Parameters</h2>
	<div class="field">
		<label>Trials
			<input type="number" bind:value={trials} min="1" />
		</label>
	</div>
	<div class="field">
		<label>Max concurrent
			<input type="number" bind:value={max_concurrent} min="1" />
		</label>
	</div>
	<div class="field">
		<label>Timeout (s)
			<input type="number" bind:value={timeout} min="1" />
		</label>
	</div>
</div>

<div class="card">
	<h2 class="panel-title">Actions</h2>
	<div class="actions">
		<button class="btn" on:click={() => runBenchmark()} disabled={running}>Run benchmark</button>
	</div>
	{#if status}
		<div class="progress-note">{status}</div>
	{/if}
</div>

{#if rows.length}
	<div class="card">
		<h2 class="panel-title">Results</h2>
		<table>
			<thead>
				<tr>
					<th>Task</th>
					<th>TTFT (s)</th>
					<th>Tok/s</th>
					<th>Iters/s</th>
					<th>Quality</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.task_id + row.engine)}
					<tr>
						<td>{row.task_id}</td>
						<td>{row.ttft_s.toFixed(3)}</td>
						<td>{row.tok_per_s.toFixed(1)}</td>
						<td>{row.iters_per_s.toFixed(2)}</td>
						<td>{#if row.quality_passed}<span class="ok">pass</span>{:else}<span class="fail">fail</span>{/if}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

{#if errors.length}
	<div class="card">
		<h2 class="panel-title">Errors</h2>
		<div class="log">{errors.map((e) => e.message).join('\n')}</div>
	</div>
{/if}

<style>
	.page-header h1 {
		margin-bottom: 0.25rem;
	}
	.subtitle {
		margin-top: 0;
		color: var(--color-muted);
	}
	.checkbox {
		font-weight: normal;
	}
	.spinner {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-muted);
	}
	.error {
		color: var(--color-danger);
	}
	.actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 1rem;
	}
	.progress-note {
		margin-top: 0.75rem;
	}
</style>
