<script lang="ts">
	import type { HoldingDraft } from '$api/client';

	let {
		holding,
		editable = false,
		onremove
	}: { holding: HoldingDraft; editable?: boolean; onremove?: () => void } = $props();
</script>

<tr>
	{#if editable}
		<td><input class="cell" bind:value={holding.ticker} /></td>
		<td><input class="cell num" type="number" bind:value={holding.quantity} /></td>
		<td><input class="cell num" type="number" bind:value={holding.cost_per_share} /></td>
		<td><input class="cell" type="date" bind:value={holding.acquired} /></td>
		<td class="right">
			<button class="remove" onclick={onremove} aria-label="Remove">×</button>
		</td>
	{:else}
		<td>{holding.ticker}</td>
		<td class="num">{holding.quantity}</td>
		<td class="num">{holding.cost_per_share}</td>
		<td>{holding.acquired}</td>
		<td></td>
	{/if}
</tr>

<style>
	td {
		padding: 7px var(--space-3) 7px 0;
		border-bottom: 1px solid var(--border);
		font-size: 13.5px;
	}
	.num {
		font-variant-numeric: tabular-nums;
	}
	.right {
		text-align: right;
	}
	.cell {
		width: 100%;
		border: 1px solid var(--border);
		border-radius: var(--radius-xs);
		padding: 5px 8px;
		font-size: 13px;
		font-family: inherit;
	}
	.cell:focus {
		outline: none;
		border-color: var(--primary);
	}
	.cell.num {
		width: 96px;
	}
	.remove {
		background: transparent;
		border: none;
		color: var(--text-faint);
		font-size: 18px;
		line-height: 1;
		padding: 0 6px;
	}
	.remove:hover {
		color: var(--danger);
	}
</style>
