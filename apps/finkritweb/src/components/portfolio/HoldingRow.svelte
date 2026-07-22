<script lang="ts">
	// One holding, in display or edit mode. The edit inputs bind to the real
	// store draft (passed in as `holding`), while weight and cost basis arrive
	// pre-derived from the table so this row does no arithmetic of its own.
	import type { HoldingDraft } from '$api/client';
	import MeterBar from '$components/ui/MeterBar.svelte';
	import { money, percent, shares } from '$lib/format';

	let {
		holding,
		weight,
		costBasis,
		currency,
		editable = false,
		onremove
	}: {
		holding: HoldingDraft;
		weight: number;
		costBasis: number;
		currency: string;
		editable?: boolean;
		onremove?: () => void;
	} = $props();
</script>

<tr>
	{#if editable}
		<td><input class="cell" bind:value={holding.ticker} /></td>
		<td class="w"><MeterBar fraction={weight} color="var(--primary-strong)" /></td>
		<td><input class="cell num" type="number" bind:value={holding.quantity} /></td>
		<td><input class="cell num" type="number" bind:value={holding.cost_per_share} /></td>
		<td class="num money">{money(costBasis, currency)}</td>
		<td><input class="cell" type="date" bind:value={holding.acquired} /></td>
		<td class="right">
			<button class="remove" onclick={onremove} aria-label="Remove holding">×</button>
		</td>
	{:else}
		<td>
			<span class="ticker">{holding.ticker}</span>
			{#if holding.confidence_note}
				<span class="note" title={holding.confidence_note}>needs review</span>
			{/if}
		</td>
		<td class="w">
			<div class="meter">
				<MeterBar fraction={weight} color="var(--primary-strong)" />
				<span class="pct">{percent(weight)}</span>
			</div>
		</td>
		<td class="num">{shares(holding.quantity)}</td>
		<td class="num">{money(holding.cost_per_share, currency)}</td>
		<td class="num money">{money(costBasis, currency)}</td>
		<td class="date">{holding.acquired}</td>
	{/if}
</tr>

<style>
	td {
		padding: 13px var(--space-3) 13px 0;
		border-bottom: 1px solid var(--border);
		font-size: 15px;
		vertical-align: middle;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.money {
		font-weight: 600;
	}
	.right {
		text-align: right;
	}
	.ticker {
		font-weight: 600;
	}
	.note {
		margin-left: var(--space-2);
		font-size: 10.5px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.02em;
		color: var(--primary-strong);
		background: var(--primary-softer);
		border: 1px solid var(--primary-soft);
		border-radius: 999px;
		padding: 1px 7px;
		cursor: help;
	}
	.w {
		width: 180px;
	}
	.meter {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.pct {
		font-size: 13.5px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
		min-width: 46px;
		text-align: right;
	}
	.date {
		color: var(--text-muted);
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
		text-align: right;
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
