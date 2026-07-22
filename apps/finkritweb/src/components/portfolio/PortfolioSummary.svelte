<script lang="ts">
	// A row of headline stats derived from the parsed holdings. No market data,
	// everything here comes straight from cost basis and dates. Recomputes as
	// the user edits the table, since overview() runs over the reactive store.
	import StatCard from '$components/ui/StatCard.svelte';
	import { overview } from '$lib/portfolio/metrics';
	import { money, percent } from '$lib/format';
	import { portfolio } from '$stores/portfolio.svelte';

	const o = $derived(overview(portfolio.holdings));

	// A compact year range for the card. The full dates live in the table, so
	// years are enough here and always fit without truncating.
	const span = $derived.by(() => {
		if (!o.earliestAcquired || !o.latestAcquired) return '—';
		const from = o.earliestAcquired.slice(0, 4);
		const to = o.latestAcquired.slice(0, 4);
		return from === to ? from : `${from} → ${to}`;
	});
</script>

<div class="grid">
	<StatCard label="Holdings" value={String(o.count)} sub="positions" />
	<StatCard
		label="Cost basis"
		value={money(o.totalCostBasis, o.currency)}
		sub={o.mixedCurrency ? 'mixed currencies' : 'total invested'}
		accent
	/>
	<StatCard
		label="Largest"
		value={o.largest ? o.largest.ticker : '—'}
		sub={o.largest ? `${percent(o.largest.weight)} of book` : ''}
	/>
	<StatCard label="Acquired" value={span} sub="first to last lot" />
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-3);
	}
	@media (max-width: 420px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}
</style>
