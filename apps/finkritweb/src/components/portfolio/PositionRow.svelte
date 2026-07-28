<script lang="ts">
	// The collapsed summary of a position built from several tax lots. Shows the
	// totals and the blended cost per share, and toggles its lots open.
	//
	// Always read only, even in edit mode. The numbers on this row are derived
	// from the lots, so there is nothing here to write back to. Editing happens
	// on the lot rows underneath.
	import type { PositionGroup } from '$lib/portfolio/metrics';
	import MeterBar from '$components/ui/MeterBar.svelte';
	import { money, percent, shares } from '$lib/format';

	let {
		group,
		currency,
		expanded = false,
		editable = false,
		ontoggle
	}: {
		group: PositionGroup;
		currency: string;
		expanded?: boolean;
		editable?: boolean;
		ontoggle: () => void;
	} = $props();

	// The chevron and the ticker are one control, so clicking either expands and
	// there is a single stop in the tab order rather than two that do the same
	// thing.
	const label = $derived(
		`${expanded ? 'Hide' : 'Show'} the ${group.lots.length} lots that make up ${group.ticker}`
	);
	const dates = $derived(group.lots.map((lot) => lot.acquired).filter(Boolean).sort());
	const spansDates = $derived(dates.length > 1 && dates[0] !== dates[dates.length - 1]);
</script>

<tr class="position" class:open={expanded}>
	<td>
		<button class="disclosure" onclick={ontoggle} aria-expanded={expanded} aria-label={label}>
			<svg class="chevron" viewBox="0 0 10 10" aria-hidden="true">
				<path d="M3 1.5 L7 5 L3 8.5" fill="none" stroke="currentColor" stroke-width="1.6"
					stroke-linecap="round" stroke-linejoin="round" />
			</svg>
			<span class="ticker">{group.ticker}</span>
			<span class="lots">{group.lots.length} lots</span>
		</button>
		{#if group.confidence_note}
			<span class="note" title={group.confidence_note}>needs review</span>
		{/if}
	</td>
	<td class="w">
		<div class="meter">
			<MeterBar fraction={group.weight} color="var(--primary-strong)" />
			<span class="pct">{percent(group.weight)}</span>
		</div>
	</td>
	<td class="num">{shares(group.quantity)}</td>
	<td class="num">
		{money(group.cost_per_share, currency)}
		<span class="avg">avg</span>
	</td>
	<td class="num money">{money(group.costBasis, currency)}</td>
	<td class="date">
		{#if spansDates}
			<span title="First of {group.lots.length} purchases, expand for all">{dates[0]}</span>
		{:else}
			{group.acquired}
		{/if}
	</td>
	{#if editable}<td></td>{/if}
</tr>

<style>
	td {
		padding: 9px var(--space-3) 9px 0;
		border-bottom: 1px solid var(--border);
		font-size: 0.9375rem;
		vertical-align: middle;
	}
	/* No bottom rule while the lots are showing, so the position and its lots
	   read as one block instead of separate rows. */
	.open td {
		border-bottom-color: transparent;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.money {
		font-weight: 600;
	}
	.date {
		color: var(--text-muted);
	}
	.disclosure {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		background: transparent;
		border: none;
		padding: 0;
		font: inherit;
		color: inherit;
		cursor: pointer;
		border-radius: var(--radius-xs);
	}
	.disclosure:focus-visible {
		outline: 2px solid var(--primary);
		outline-offset: 3px;
	}
	.chevron {
		width: 10px;
		height: 10px;
		flex: none;
		color: var(--text-faint);
		transition: transform 0.15s ease;
	}
	.open .chevron {
		transform: rotate(90deg);
	}
	.disclosure:hover .chevron {
		color: var(--text-muted);
	}
	.ticker {
		font-weight: 600;
	}
	.disclosure:hover .ticker {
		color: var(--primary-strong);
	}
	.lots {
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--text-muted);
		background: var(--surface-2);
		border-radius: 999px;
		padding: 1px 7px;
	}
	.avg {
		margin-left: 4px;
		font-size: 0.6875rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: var(--text-faint);
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
</style>
