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
		<nav class="menu">
			<a href="/" class:active={active === '/'}>Dashboard</a>
			<a href="/run" class:active={active === '/run'}>Run</a>
			<a href="/corpus" class:active={active === '/corpus'}>Corpus</a>
		</nav>
	</header>

	<div class="theme-toggle">
		<button on:click={toggleTheme}>
			{isDark ? '☀️ Light Mode' : '🌙 Dark Mode'}
		</button>
	</div>

	<main class="content">
		<slot />
	</main>
</div>
