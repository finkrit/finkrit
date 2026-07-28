<script lang="ts">
	// A titled block: a small heading with an optional right side hint, over its
	// content. Keeps the view from repeating heading markup for every section.
	import type { Snippet } from 'svelte';

	let {
		title,
		hint,
		children
	}: { title: string; hint?: string; children: Snippet } = $props();
</script>

<section class="block">
	<div class="bar">
		<h2>{title}</h2>
		{#if hint}<span class="hint">{hint}</span>{/if}
	</div>
	{@render children()}
</section>

<style>
	.block {
		display: flex;
		flex-direction: column;
	}
	.bar {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin-bottom: var(--space-3);
	}
	h2 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		letter-spacing: 0.03em;
		text-transform: uppercase;
		color: var(--text-muted);
	}
	.hint {
		font-size: 0.8125rem;
		color: var(--text-faint);
	}
</style>
