<script lang="ts">
	import '../styles/global.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	const ls = typeof localStorage !== 'undefined' ? localStorage : null;

	let active = '';
	let appClass = '';
	let isDark = ls ? ls.getItem('theme') === 'dark' : false;

	// Single source of truth: isDark drives both the div class and the
	// <html> class, applied reactively so they can never desync.
	$: {
		if (typeof document !== 'undefined') {
			document.documentElement.classList.toggle('dark', isDark);
			if (ls) ls.setItem('theme', isDark ? 'dark' : 'light');
		}
		appClass = isDark ? 'app dark' : 'app';
	}

	onMount(() => {
		page.subscribe((value) => {
			active = value.url.pathname;
		});

		// Listen for theme changes in the browser/system
		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
			if (!ls) return;
			if (!ls.getItem('theme')) {
				isDark = e.matches;
				dispatch('themeChange', { dark: isDark });
			}
		});
	});

	function toggleTheme() {
		isDark = !isDark;
		dispatch('themeChange', { dark: isDark });
	}
</script>

<div class={appClass}>
	<header class="topbar">
		<div class="brand">
			<h1>Local LLM Benchmark</h1>
		</div>
		<div class="theme-toggle">
			<button on:click={toggleTheme} aria-label="Toggle theme">
				{#if isDark}
					<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
				{:else}
				<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
			{/if}
			</button>
		</div>
</header>

	<header class="subnav">
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