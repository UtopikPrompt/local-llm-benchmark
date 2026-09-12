<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { loadCorpus, saveCorpus } from '$lib/storage/index.js';
import { buildDefaultCorpus } from '$lib/corpus/tasks.js';
import type { Category, Task } from '$lib/corpus/tasks.js';

	let active = '';
	let status = '';

	let taskIds = '';
	let taskCategories = '';
	let taskPrompts = '';
	let taskSystems = '';
	let taskExpected = '';
	let taskValidators = '';
	let corpus = { tasks: buildDefaultCorpus() };
	// Autosave: debounced write to IndexedDB on any change, so no Save
	// button is required.
	let ready = false;
	let savedSignature = '';
	let saveTimer = 0;

	function currentSignature(): string {
		return corpus.tasks
			.map(
				(t) =>
					`${t.id}\u0000${t.category}\u0000${t.prompt}\u0000${t.system ?? ''}\u0000${t.expected ?? ''}\u0000${t.validate ?? ''}`,
			)
			.join('\n');
	}

	onMount(async () => {
		page.subscribe((value) => {
			active = value.url.pathname;
		});
		corpus = await loadCorpus();
		ready = true;
		savedSignature = currentSignature();
	});

	$: {
		if (ready && typeof document !== 'undefined') {
			if (savedSignature !== currentSignature()) {
				savedSignature = currentSignature();
				clearTimeout(saveTimer);
				saveTimer = setTimeout(async () => {
					await persistCorpus();
				}, 400);
			}
		}
	}

	function emptyTask(): Task {
		return {
			id: '',
			category: 'qa',
			prompt: '',
			system: null,
			expected: null,
			validate: null,
		};
	}

	function resetToDefaults(): void {
		corpus = { tasks: buildDefaultCorpus() };
	}

	function removeTask(index: number): void {
		corpus.tasks.splice(index, 1);
	}

	async function persistCorpus(): Promise<void> {
		await saveCorpus(corpus);
	}
</script>

<div class="page-header">
	<h1>Corpus</h1>
	<p class="subtitle">Configure the tasks the benchmark asks the engine to answer.</p>
</div>

<div class="card">
	<h2 class="panel-title">Tasks</h2>
	<ul>
		{#each corpus.tasks as task, index (task.id + index)}
			<li class="task">
				<div class="task-title">{task.id}</div>
				<div class="task-meta">
					<span class="badge">{task.category}</span>
					{#if task.validate}<span class="ok">validated</span>{/if}
				</div>
				<div class="task-prompt">{task.prompt}</div>
				{#if task.system}
					<div class="task-system"><strong>System:</strong> {task.system}</div>
				{/if}
				{#if task.expected}
					<div class="task-expected"><strong>Expected:</strong> {task.expected}</div>
				{/if}
				<button class="btn secondary small" on:click={() => removeTask(index)}>Remove</button>
			</li>
		{/each}
	</ul>
	<div class="actions">
		<button class="btn secondary" on:click={resetToDefaults}>Reset to defaults</button>
	</div>
</div>

<div class="card">
	<h2 class="panel-title">Add task</h2>
	<div class="field">
		<label>ID
			<input bind:value={taskIds} placeholder="my-task" />
		</label>
	</div>
	<div class="field">
		<label>Category
			<select bind:value={taskCategories}>
				<option value="doc">doc</option>
				<option value="code">code</option>
				<option value="qa">qa</option>
				<option value="math">math</option>
			</select>
		</label>
	</div>
	<div class="field">
		<label>Prompt
			<textarea bind:value={taskPrompts} rows="3"></textarea>
		</label>
	</div>
	<div class="field">
		<label>System (optional)
			<textarea bind:value={taskSystems} rows="2"></textarea>
		</label>
	</div>
	<div class="field">
		<label>Expected answer
			<input bind:value={taskExpected} placeholder="e.g. GET" />
		</label>
	</div>
	<div class="field">
		<label>Validator (JS expression, optional)
			<input bind:value={taskValidators} placeholder="true" />
		</label>
	</div>
	<button class="btn">Add task</button>
</div>

{#if status}
	<div class="progress-note">{status}</div>
{/if}

<style>
	.page-header h1 {
		margin-bottom: 0.25rem;
	}
	.subtitle {
		margin-top: 0;
		color: var(--color-muted);
	}
	.task {
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1rem;
	}
	.task-title {
		font-weight: 600;
	}
	.task-meta {
		display: flex;
		gap: 0.5rem;
		margin: 0.5rem 0;
	}
	.task-prompt {
		color: var(--color-muted);
		font-size: 0.9rem;
		margin: 0.25rem 0;
	}
	.task-system {
		font-size: 0.85rem;
		color: var(--color-muted);
	}
	.task-expected {
		overflow: hidden;
	}
	.actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 1rem;
	}
	.field {
		margin-bottom: 1rem;
	}
	.field label {
		display: block;
		font-weight: 500;
		margin-bottom: 0.25rem;
	}
	.field input,
	.field select,
	.field textarea {
		width: 100%;
		padding: 0.45rem 0.6rem;
		border: 1px solid var(--color-border);
		border-radius: 6px;
		font-size: 0.9rem;
	}
	.field textarea {
		min-height: 6rem;
	}
	.progress-note {
		margin-top: 1rem;
		color: var(--color-muted);
	}
</style>
