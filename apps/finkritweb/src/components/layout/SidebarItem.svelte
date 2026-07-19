<script lang="ts">
	import Icon from '$components/ui/Icon.svelte';
	import { ui, type ViewId } from '$stores/ui.svelte';

	let {
		label,
		icon,
		view,
		disabled = false
	}: {
		label: string;
		icon: 'holdings' | 'risk' | 'lock';
		view?: ViewId;
		disabled?: boolean;
	} = $props();

	const active = $derived(!disabled && view !== undefined && ui.view === view);
</script>

<button
	class="item"
	class:active
	{disabled}
	onclick={() => view && ui.select(view)}
>
	<span class="icon"><Icon name={icon} size={16} /></span>
	<span class="label">{label}</span>
</button>

<style>
	.item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		width: 100%;
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		padding: 8px var(--space-2);
		color: var(--text-muted);
		font-size: 13.5px;
		font-weight: 450;
		text-align: left;
	}
	.item:not(:disabled):hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.item.active {
		background: var(--primary-soft);
		color: var(--primary-strong);
		font-weight: 550;
	}
	.item:disabled {
		color: var(--text-faint);
		cursor: default;
	}
	.icon {
		display: inline-flex;
		flex-shrink: 0;
	}
</style>
