<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { BenchmarkError } from '$lib/errors.js';
	import { DEFAULTS } from '$lib/config.js';
	import { loadEngines, saveEngines } from '$lib/storage/index.js';
import { buildDefaultCorpus } from '$lib/corpus/tasks.js';
import type { Category, Task } from '$lib/corpus/tasks.js';
	let engines: EngineConfig[] = [];

	onMount(async () => {
		engines = await loadEngines();
		page.subscribe((value) => {
			active = value.url.pathname;
		});
	});

	let active = '';

	let engineName = DEFAULTS.engine_base_url;
	let engineBaseUrl = DEFAULTS.engine_base_url;
	let engineModel = DEFAULTS.engine_model;
	let judgeName = DEFAULTS.judge_base_url;
	let judgeBaseUrl = DEFAULTS.judge_base_url;
	let judgeModel = DEFAULTS.judge_model;
	let taskCategory = 'all';
	let taskSystems = '' as string[];
	let taskIds = '' as string[];
	let taskExpected = '' as string[];
	let trials = DEFAULTS.trials;
	let maxConcurrent = DEFAULTS.max_concurrent;
	let timeout = DEFAULTS.timeout;
	let useJudge = false;

	let saving = false;
	let running = false;
	let status = '' as string;
	let rows: Row[] = [];
	let errors: BenchmarkError[] = [];

	async function saveConfig(): Promise<void> {
		const config: BenchmarkConfig = {
			engines: [
				{
					name: engineName,
					base_url: engineBaseUrl,
					model: engineModel,
					timeout,
					max_concurrent: maxConcurrent,
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
			tasks: taskIds,
		};
		await saveEngines(config.engines);
		status = 'config saved';
	}

	function buildTasks(): Task[] {
		const systems = taskSystems.split('\n').map((s) => s.trim()).filter(Boolean);
		const expected = taskExpected.split('\n').map((s) => s.trim()).filter(Boolean);
		return taskIds
			.split('\n')
			.map((id) => id.trim())
			.filter(Boolean)
			.map((id, index) => ({
				id,
				category: taskCategory === 'all' ? 'qa' : taskCategory,
				prompt: id,
				system: systems[index] ?? null,
				expected: expected[index] ?? null,
				validate: null,
			}));
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
			};
			const result = await runner(config);
			rows = result.rows;
			status = `done: ${rows.length} rows in ${result.elapsed_s.toFixed(2)}s`;
		} catch (error) {
			errors.push(error instanceof BenchmarkError ? error : new BenchmarkError('INVALID', String(error)));
			status = 'error';
		} finally {
			running = false;
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
		<label>Engine name</label>
		<input bind:value={engineName} placeholder="Ollama" />
	</div>
	<div class="field">
		<label>Base URL</label>
		<input bind:value={engineBaseUrl} placeholder="http://localhost:11434" />
	</div>
	<div class="field">
		<label>Model</label>
		<input bind:value={engineModel} placeholder="llama3" />
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
			<label>Judge name</label>
			<input bind:value={judgeName} placeholder="judge" />
		</div>
		<div class="field">
			<label>Judge base URL</label>
			<input bind:value={judgeBaseUrl} placeholder="http://localhost:11434" />
		</div>
		<div class="field">
			<label>Judge model</label>
			<input bind:value={judgeModel} placeholder="gamma4:e4b" />
		</div>
	{/if}
</div>

<div class="card">
	<h2 class="panel-title">Tasks</h2>
	<div class="field">
		<label>Category</label>
		<select bind:value={taskCategory}>
			<option value="all">All</option>
			<option value="doc">doc</option>
			<option value="code">code</option>
			<option value="qa">qa</option>
			<option value="math">math</option>
		</select>
	</div>
	<div class="field">
		<label>Task IDs (one per line)</label>
		<textarea bind:value={taskIds} placeholder="doc-rest-api" rows="6"></textarea>
	</div>
	<div class="field">
		<label>Systems (one per line)</label>
		<textarea bind:value={taskSystems} rows="3"></textarea>
	</div>
	<div class="field">
		<label>Expected answers (one per line)</label>
		<textarea bind:value={taskExpected} rows="3"></textarea>
	</div>
</div>

<div class="card">
	<h2 class="panel-title">Parameters</h2>
	<div class="field">
		<label>Trials</label>
		<input type="number" bind:value={trials} min="1" />
	</div>
	<div class="field">
		<label>Max concurrent</label>
		<input type="number" bind:value={maxConcurrent} min="1" />
	</div>
	<div class="field">
		<label>Timeout (s)</label>
		<input type="number" bind:value={timeout} min="1" />
	</div>
</div>

<div class="card">
	<h2 class="panel-title">Actions</h2>
	<div class="actions">
		<button class="btn secondary" on:click={() => saveConfig()} disabled={saving}>Save config</button>
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
	.actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 1rem;
	}
	.progress-note {
		margin-top: 0.75rem;
	}
</style>
