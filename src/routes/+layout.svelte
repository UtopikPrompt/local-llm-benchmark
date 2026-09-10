<script lang="ts">
	import '../styles/global.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	let active = '';
	onMount(() => {
		page.subscribe((value) => {
			active = value.url.pathname;
		});
	});
</script>

<div class="app">
	<header class="topbar">
		<div class="brand">
			<h1>Local LLM Benchmark</h1>
		</div>
		<nav class="menu">
			<a href="/" class:active={active === '/'}>Dashboard</a>
			<a href="/run" class:active={active === '/run'}>Run</a>
			<a href="/corpus" class:active={active === '/corpus'}>Corpus</a>
		</nav>
	</header>

	<main class="content">
		<slot />
	</main>
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		font-family: 'Inter', system-ui, sans-serif;
		color: #1f2430;
	}
	.topbar {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.5rem;
		background: #f6f7f9;
		border-bottom: 1px solid #e2e6ec;
		padding: 0 1.25rem;
	}
	.brand h1 {
		font-family: 'Space Grotesk', sans-serif;
		font-size: 1.1rem;
		margin-bottom: 0;
	}
	.topbar nav {
		display: flex;
		gap: 0.5rem;
	}
	.topbar nav a {
		padding: 0.6rem 0.9rem;
		color: #475467;
		text-decoration: none;
		border-radius: 6px;
		font-weight: 500;
	}
	.topbar nav a:hover {
		background: #e9edf2;
	}
	.topbar nav a.active {
		background: #2563eb;
		color: #fff;
	}
	.content {
		padding: 1.5rem 2rem;
		max-width: 1100px;
		width: 100%;
	}
</style>
