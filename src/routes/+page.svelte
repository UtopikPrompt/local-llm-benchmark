<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { Chart } from 'chart.js';
	import type { Chart as ChartType } from 'chart.js';
	import type { Row } from '$lib/results.js';
	import { loadRows } from '$lib/storage/index.js';
	import { CATEGORIES } from '$lib/ui.js';

	let rows: Row[] = [];
	let canvas: HTMLCanvasElement | null = null;
	let chart: ChartType | null = null;

	function filtered(): Row[] {
		return rows.filter((row) => {
			if (engineFilter && row.engine !== engineFilter) return false;
			if (modelFilter && row.model !== modelFilter) return false;
			if (categoryFilter && row.category !== categoryFilter) return false;
			if (qualityFilter === 'pass' && !row.quality_passed) return false;
			if (qualityFilter === 'fail' && row.quality_passed) return false;
			return true;
		});
	}

	function series(): { label: string; data: number[] }[] {
		const data = filtered().map((row) => row.tok_per_s);
		return [
			{ label: 'tok/s', data },
			{ label: 'iters/s', data },
		];
	}

	let engineFilter = '';
	let modelFilter = '';
	let categoryFilter = '';
	let qualityFilter = '';

	function initChart(): void {
		if (chart) {
			chart.destroy();
			chart = null;
		}
		if (!canvas) return;
		chart = new Chart(canvas.getContext('2d'), {
			type: 'bar',
			data: {
				labels: filtered().map((row) => row.task_id),
				datasets: series(),
			},
			options: {
				responsive: true,
				plugins: {
					legend: { display: true },
					titles: { display: true, text: 'Throughput by task' },
				},
				scales: {
					x: { stacked: true, title: { display: true, text: 'Task' } },
					y: {
						type: 'logarithmic',
						stacked: true,
						title: { display: true, text: 'Tokens / second' },
					},
				},
			},
		});
	}

	function updateChart(): void {
		if (!chart) return;
		chart.data.labels = filtered().map((row) => row.task_id);
		chart.data.datasets = series();
		chart.update();
	}

	function refresh(): void {
		rows = loadRows().then((stored) => {
			rows = stored;
			updateChart();
		});
	}

	onMount(async () => {
		rows = await loadRows();
		initChart();
		page.subscribe(() => {});
	});
</script>

<div class="page-header">
	<h1>Dashboard</h1>
	<p class="subtitle">Benchmark results. Reload engines and models.</p>
</div>

<div class="filters">
	<select bind:value={engineFilter} on:change={refresh}>
		<option value="">All engines</option>
		{#each [...new Set(rows.map((r) => r.engine))] as engine (engine)}
			<option>{engine}</option>
		{/each}
	</select>
	<select bind:value={modelFilter} on:change={refresh}>
		<option value="">All models</option>
		{#each [...new Set(rows.map((r) => r.model))] as model (model)}
			<option>{model}</option>
		{/each}
	</select>
	<select bind:value={categoryFilter} on:change={refresh}>
		<option value="">All</option>
		{#each CATEGORIES as category (category)}
			<option>{category}</option>
		{/each}
	</select>
	<select bind:value={qualityFilter} on:change={refresh}>
		<option value="">All</option>
		<option value="pass">pass</option>
		<option value="fail">fail</option>
	</select>
</div>

<div class="charts">
	<canvas bind:this={canvas}></canvas>
</div>

<div class="summary">
	<p>Rows: {rows.length}</p>
	<p>Passed: {rows.filter((r) => r.quality_passed).length}</p>
</div>

<div class="results">
	<table>
		<thead>
			<tr>
				<th>Engine</th>
				<th>Model</th>
				<th>Category</th>
				<th>Task</th>
				<th>TTFT (s)</th>
				<th>Tok/s</th>
				<th>Iters/s</th>
				<th>Quality</th>
			</tr>
		</thead>
		<tbody>
			{#each filtered() as row (row.task_id + row.engine)}
				<tr>
					<td>{row.engine}</td>
					<td>{row.model}</td>
					<td>{row.category}</td>
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

<style>
	.page-header h1 {
		margin-bottom: 0.25rem;
	}
	.subtitle {
		margin-top: 0;
		color: var(--color-muted);
	}
	.filters {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}
	.filters select {
		padding: 0.4rem;
		border: 1px solid var(--color-border);
		border-radius: 6px;
	}
	.charts canvas {
		max-height: 300px;
	}
	.summary {
		display: flex;
		gap: 1rem;
	}
	.results table {
		width: 100%;
		border-collapse: collapse;
	}
	.results th,
	.results td {
		text-align: left;
		padding: 0.4rem 0.6rem;
		border-bottom: 1px solid var(--color-border);
	}
	.ok {
		color: var(--color-success);
	}
	.fail {
		color: var(--color-danger);
	}
</style>
