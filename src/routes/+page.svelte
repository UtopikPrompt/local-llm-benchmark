<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
import type { Row } from '$lib/results.js';
import { loadRows } from '$lib/storage/index.js';
import { CATEGORIES } from '$lib/ui.js';
import { registerChart, Chart } from '$lib/chart/register.js';
import type { Chart as ChartType } from '$lib/chart/register.js';

	type Impact = {
		rows: number;
		passed: number;
		success: number;
		ttft: number;
		tok_s: number;
		iters_s: number;
	};
	type Health = {
		overall: number;
		metrics: { label: string; score: number; max: number; points: number; rule: string }[];
		insights: { emoji: string; message: string }[];
	};
	let rows: Row[] = [];
	let d: Impact;
	let h: Health;
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

	$: d = devImpact();
	$: h = health();

	const GRADE_COLORS = [
		'#e55349', '#ce818b', '#8957e5', '#d29922', '#3fb950',
	];
	function gradeColor(score: number): string {
		return GRADE_COLORS[Math.min(5, Math.floor(score / 20))];
	}
	function gradeLetter(score: number): string {
		if (score >= 90) return 'A';
		if (score >= 75) return 'B';
		if (score >= 60) return 'C';
		if (score >= 40) return 'D';
		return 'F';
	}
	function fmtPct(n: number): string {
		return n.toFixed(1) + '%';
	}
	function barColor(ratio: number): string {
		if (ratio >= 0.8) return 'var(--color-success)';
		if (ratio >= 0.5) return 'var(--color-warning)';
		return 'var(--color-danger)';
	}
	function fmtNum(n: number): string {
		return n.toFixed(1);
	}

	function devImpact(): {
		rows: number;
		passed: number;
		success: number;
		ttft: number;
		tok_s: number;
		iters_s: number;
	} {
		const f = filtered();
		const passed = f.filter((r) => r.quality_passed).length;
		return {
			rows: f.length,
			passed,
			success: f.length ? passed / f.length : 0,
			ttft: f.length ? f.reduce((s, r) => s + r.ttft_s, 0) / f.length : 0,
			tok_s: f.length ? f.reduce((s, r) => s + r.tok_per_s, 0) / f.length : 0,
			iters_s: f.length ? f.reduce((s, r) => s + r.iters_per_s, 0) / f.length : 0,
		};
	}

	function health(): {
		overall: number;
		metrics: { label: string; score: number; max: number; points: number; rule: string }[];
		insights: { emoji: string; message: string }[];
	} {
		const f = filtered();
		if (!f.length) {
			return { overall: 0, metrics: [], insights: [] };
		}
		const passed = f.filter((r) => r.quality_passed).length;
		const success = passed / f.length;
		const ttft = f.reduce((s, r) => s + r.ttft_s, 0) / f.length;
		const iters = f.reduce((s, r) => s + r.iters_per_s, 0) / f.length;
		const tok = f.reduce((s, r) => s + r.tok_per_s, 0) / f.length;
		const deterministic = f.filter((r) => r.quality_deterministic).length;

		const quality = Math.round(success * 100);
		const speed = Math.min(100, Math.round((1 - Math.min(ttft, 5)) / 5 * 100));
		const itersScore = Math.min(100, Math.round(iters * 8));
		const tokScore = Math.min(100, Math.round(tok * 4));
		const consistency = Math.round((deterministic / f.length) * 100);

		const overall = Math.round(
			(quality * 0.4 + speed * 0.2 + itersScore * 0.2 + tokScore * 0.1 + consistency * 0.1),
		);

		const metrics = [
			{
				label: 'Completion',
				score: quality,
				max: 100,
				points: passed,
				rule: 'Deterministic pass rate across all trials',
			},
			{
				label: 'Speed',
				score: speed,
				max: 100,
				points: Math.round((speed / 100) * 5),
				rule: 'TTFT under 5s',
			},
			{
				label: 'Iters/s',
				score: itersScore,
				max: 100,
				points: Math.round((iters / 12.5) * 5),
				rule: '≥8 iters/s',
			},
			{
				label: 'Throughput',
				score: tokScore,
				max: 100,
				points: Math.round((tok / 5) * 5),
				rule: '≥5 tok/s',
			},
		];

		const insights: { emoji: string; message: string }[] = [];
		if (success < 1) {
			insights.push({
				emoji: '🎯',
				message: `${f.length - passed} trial(s) failed — check the tasks and outputs in the Run view.`,
			});
		}
		if (ttft > 1.5) {
			insights.push({
				emoji: '💡',
				message: `Avg TTFT ${ttft.toFixed(1)}s — a system prompt / rehydration brief often cuts this.`,
			});
		}
		if (iters < 6) {
			insights.push({
				emoji: '🧩',
				message: 'Low iteration rate — a custom skill/agent config can push repeated work through faster.',
			});
		}
		insights.push({
			emoji: '✅',
			message: 'Benchmark data loaded — reload engines and models to refresh.',
		});
		return { overall, metrics, insights };
	}

	function initChart(): void {
		if (chart) {
			chart.destroy();
			chart = null;
		}
		if (!canvas) return;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		chart = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: filtered().map((row) => row.task_id),
				datasets: series(),
			},
			options: {
				responsive: true,
				plugins: {
					legend: { display: true },
					title: { display: true, text: 'Throughput by task' },
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
		loadRows().then((stored) => {
			rows = stored as Row[];
			updateChart();
		});
	}

	onMount(async () => {
		registerChart();
		rows = await loadRows();
		initChart();
		page.subscribe(() => {});
	});
</script>

<div class="page-header">
	<h1>Dashboard</h1>
	<p class="subtitle">Benchmark results. Reload engines and models.</p>
</div>

<div class="section">
	<h2>⏱ Developer Impact — This Run</h2>
	<div class="cards">
		<div class="mini-card">
			<div class="mini-label">Trials</div>
			<div class="mini-val data-text">{d.rows}</div>
		</div>
		<div class="mini-card">
			<div class="mini-label">Passed</div>
			<div class="mini-val data-text">{d.passed}</div>
		</div>
		<div class="mini-card">
			<div class="mini-label">Success</div>
			<div class="mini-val data-text" style="color:var(--color-success)">{fmtPct(d.success)}</div>
		</div>
		<div class="mini-card">
			<div class="mini-label">Avg TTFT</div>
			<div class="mini-val data-text">{d.ttft.toFixed(2)}s</div>
		</div>
		<div class="mini-card">
			<div class="mini-label">Throughput</div>
			<div class="mini-val data-text">{d.tok_s.toFixed(1)}</div>
		</div>
		<div class="mini-card">
			<div class="mini-label">Iteration</div>
			<div class="mini-val data-text">{d.iters_s.toFixed(2)}</div>
		</div>
	</div>
</div>

<div class="section" style="border-top:3px solid {gradeColor(h.overall)};">
	<div class="score-row">
		<div class="grade-box">
			<div class="grade-letter">{gradeLetter(h.overall)}</div>
			<div class="grade-label">AI Health</div>
		</div>
		<div class="score-main">
			<div class="score-title">Usage Health Score <span class="data-text" style="color:{gradeColor(h.overall)}">{fmtNum(h.overall)}/100</span></div>
			<div class="bar-track">
				<div class="bar-fill" style="width:{h.overall}%;background:{gradeColor(h.overall)}"></div>
			</div>
		</div>
	</div>
	<div class="score-metrics">
		{#each h.metrics as m}
			<div class="metric">
				<div class="metric-top">
					<span>{m.label}</span>
					<span class="data-text">{m.points}/{m.max}</span>
				</div>
				<div class="bar-track">
					<div class="bar-fill" style="width:{(m.score / m.max) * 100}%;background:{barColor(m.score / m.max)}"></div>
				</div>
			</div>
		{/each}
	</div>
	<div class="insights">
		<div class="insights-head">Insights</div>
		<ul>
			{#each h.insights as ins}
				<li>
					<span class="insight-emoji">{ins.emoji}</span>
					<span class="insight-msg">{ins.message}</span>
				</li>
			{/each}
		</ul>
	</div>
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
	<p>Passed: {d.passed}</p>
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
	.subtitle {
		margin-top: 0;
		color: var(--color-muted);
	}
	.filters {
		display: flex;
		gap: 0.75rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}
	.filters select {
		padding: 0.5rem 0.6rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		background: var(--color-bg);
		color: var(--color-text);
		font-size: 0.9rem;
		min-width: 16rem;
	}
	.charts canvas {
		max-height: 300px;
	}
	.summary {
		display: flex;
		gap: 1.5rem;
		flex-wrap: wrap;
	}
	.cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
		gap: 0.75rem;
	}
	.mini-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: 0.65rem 0.75rem;
	}
	.mini-label {
		display: block;
		color: var(--color-muted);
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		margin-bottom: 0.15rem;
	}
	.mini-val {
		display: flex;
		align-items: baseline;
		gap: 0.35rem;
		font-variant-numeric: tabular-nums;
		font-family: var(--font-data);
		font-size: 1.15rem;
	}
	.score-row {
		display: flex;
		align-items: center;
		gap: 1rem;
	}
	.grade-box {
		width: 3.75rem;
		height: 3.75rem;
		border-radius: 50%;
		display: grid;
		place-items: center;
		font-family: var(--font-data);
		font-weight: 700;
		font-size: 1.6rem;
		flex: none;
	}
	.score-main {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.score-main .val {
		font-family: var(--font-data);
		font-size: 1.6rem;
		font-weight: 700;
	}
	.score-main .lbl {
		color: var(--color-muted);
		font-size: 0.8rem;
	}
	.bar-track {
		flex: 1;
		max-width: 22rem;
		height: 0.75rem;
		border-radius: 999px;
		background: var(--color-border);
		overflow: hidden;
	}
	.bar-fill {
		height: 100%;
		border-radius: 999px;
		transition: width 0.6s ease;
	}
	.score-metrics {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
		gap: 0.75rem;
		margin-top: 0.75rem;
	}
	.metric {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: 0.6rem 0.75rem;
	}
	.metric-top {
		display: flex;
		justify-content: space-between;
		font-size: 0.78rem;
		color: var(--color-muted);
		margin-bottom: 0.4rem;
	}
	.metric .bar-track {
		max-width: none;
	}
	.insights {
		margin-top: 0.75rem;
	}
	.insights-head {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		margin-bottom: 0.5rem;
	}
	.insight-emoji {
		font-size: 1.1rem;
		flex: none;
	}
	.insights ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.insight-msg {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.85rem;
	}
	.results {
		border-top: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		overflow: hidden;
	}
	.results table {
		width: 100%;
		border-collapse: collapse;
	}
	.results th,
	.results td {
		text-align: left;
		padding: 0.65rem 0.85rem;
		border-bottom: 1px solid var(--color-border);
	}
	.results th:first-child,
	.results td:first-child {
		border-left: 1px solid var(--color-border);
	}
	.results th:last-child,
	.results td:last-child {
		border-right: 1px solid var(--color-border);
	}
	.ok {
		color: var(--color-success);
	}
	.fail {
		color: var(--color-danger);
	}
</style>
