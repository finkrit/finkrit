<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		variant = 'primary',
		type = 'button',
		disabled = false,
		onclick,
		children
	}: {
		variant?: 'primary' | 'ghost';
		type?: 'button' | 'submit';
		disabled?: boolean;
		onclick?: () => void;
		children: Snippet;
	} = $props();
</script>

<button class="btn {variant}" {type} {disabled} {onclick}>
	{@render children()}
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		border: 1px solid transparent;
		border-radius: var(--radius-sm);
		padding: 8px 14px;
		font-size: 13px;
		font-weight: 500;
		transition:
			background 0.12s ease,
			border-color 0.12s ease,
			opacity 0.12s ease;
	}
	.btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.primary {
		background: var(--primary);
		color: var(--primary-contrast);
	}
	.primary:not(:disabled):hover {
		background: var(--primary-strong);
	}
	.ghost {
		background: transparent;
		color: var(--text-muted);
		border-color: var(--border);
	}
	.ghost:not(:disabled):hover {
		background: var(--surface-2);
		color: var(--text);
	}
</style>
