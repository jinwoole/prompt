<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import Header from '$lib/components/Header.svelte';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Prompt</title>
	<meta name="description" content="AI 프롬프트 작성 도구">
	<meta name="viewport" content="width=device-width, initial-scale=1">
</svelte:head>

<div class="min-h-screen bg-white">
	<Header />
	<main class="pt-16">
		{@render children?.()}
	</main>
</div>
