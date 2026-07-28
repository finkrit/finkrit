<script lang="ts">
	// One tax lot, in display or edit mode. The edit inputs bind to the real
	// store draft (passed in as `holding`), while weight and cost basis arrive
	// pre-derived from the table so this row does no arithmetic of its own.
	//
	// A position bought once is a single lot, so the same row serves both. When
	// it sits under a PositionRow as one of several lots, `lotLabel` is set and
	// the row indents, drops the ticker (the position above already names it),
	// and measures its bar against the position rather than the portfolio.
	import type { HoldingDraft } from '$api/client';
	import MeterBar from '$components/ui/MeterBar.svelte';
	import { money, percent, shares } from '$lib/format';

	let {
		holding,
		weight,
		costBasis,
		currency,
		editable = false,
		lotLabel = null,
		shareOfPosition = 0,
		onremove
	}: {
		holding: HoldingDraft;
		weight: number;
		costBasis: number;
		currency: string;
		editable?: boolean;
		lotLabel?: string | null;
		shareOfPosition?: number;
		onremove?: () => void;
	} = $props();

	const nested = $derived(lotLabel !== null);
</script>

<tr class:nested>
	{#if editable}
		<!-- The ticker stays editable on a nested lot. Review is where a parser
		     mistake gets corrected, and a mistyped ticker is why a lot landed
		     under the wrong position in the first place. Fixing it here regroups
		     the row. The indent, not a label, carries the nesting. -->
		<td><input class="cell" bind:value={holding.ticker} /></td>
		<td class="w">
			<MeterBar
				fraction={nested ? shareOfPosition : weight}
				color={nested ? 'var(--primary-soft)' : 'var(--primary-strong)'}
			/>
		</td>
		<td><input class="cell num" type="number" bind:value={holding.quantity} /></td>
		<td><input class="cell num" type="number" bind:value={holding.cost_per_share} /></td>
		<td class="num money">{money(costBasis, currency)}</td>
		<td><input class="cell" type="date" bind:value={holding.acquired} /></td>
		<td class="right">
			<button class="remove" onclick={onremove} aria-label="Remove holding">×</button>
		</td>
	{:else}
		<td class:lot={nested}>
			{#if nested}
				<span class="label">{lotLabel}</span>
			{:else}
				<span class="ticker">{holding.ticker}</span>
			{/if}
			{#if holding.confidence_note}
				<span class="note" title={holding.confidence_note}>needs review</span>
			{/if}
		</td>
		<td class="w">
			<div class="meter">
				<MeterBar
					fraction={nested ? shareOfPosition : weight}
					color={nested ? 'var(--primary-soft)' : 'var(--primary-strong)'}
				/>
				<span class="pct">{percent(nested ? shareOfPosition : weight)}</span>
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
		padding: 9px var(--space-3) 9px 0;
		border-bottom: 1px solid var(--border);
		font-size: 0.9375rem;
		vertical-align: middle;
	}
	/* A lot under its position. Quieter than a standalone holding, because the
	   position above is the thing being read and these are its detail. */
	.nested td {
		font-size: 0.875rem;
		color: var(--text-muted);
		background: var(--surface-1);
	}
	.nested td:first-child {
		padding-left: var(--space-4);
	}
	.lot .label {
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--text-faint);
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.money {
		font-weight: 600;
	}
	.nested .money {
		font-weight: 500;
	}
	.right {
		text-align: right;
	}
	.ticker {
		font-weight: 600;
	}
	.note {
		margin-left: var(--space-2);
		font-size: 0.6562rem;
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
		font-size: 0.8438rem;
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
		font-size: 0.8125rem;
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
		font-size: 1.125rem;
		line-height: 1;
		padding: 0 6px;
	}
	.remove:hover {
		color: var(--danger);
	}
</style>
