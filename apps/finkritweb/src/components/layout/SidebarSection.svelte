<script lang="ts">
	import type { Snippet } from 'svelte';
	import { slide } from 'svelte/transition';
	import Icon from '$components/ui/Icon.svelte';

	// A collapsible menu group, Claude-style: click the header to expand/collapse
	// its items; the chevron rotates to show state.
	let {
		title,
		open = false,
		children
	}: { title: string; open?: boolean; children: Snippet } = $props();

	// Prop is the initial default only; toggling is local thereafter. (Svelte
	// warns that $state captures `open`'s initial value -- that's the intent.)
	// svelte-ignore state_referenced_locally
	let isOpen = $state(open);
</script>

<div class="section">
	<button class="header" onclick={() => (isOpen = !isOpen)} aria-expanded={isOpen}>
		<span class="chevron" class:open={isOpen}><Icon name="chevron" size={14} /></span>
		<span class="title">{title}</span>
	</button>

	{#if isOpen}
		<div class="items" transition:slide={{ duration: 160 }}>
			{@render children()}
		</div>
	{/if}
</div>

<style>
	.section {
		margin-top: var(--space-2);
	}
	.header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		background: transparent;
		border: none;
		padding: 6px var(--space-2);
		color: var(--text-faint);
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}
	.chevron {
		display: inline-flex;
		color: var(--text-faint);
		transition: transform 0.15s ease;
		transform: rotate(-90deg);
	}
	.chevron.open {
		transform: rotate(0deg);
	}
	.items {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-top: 2px;
	}
</style>
