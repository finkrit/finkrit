<script lang="ts">
	// Weight by cost basis as a single stacked bar plus a legend. Stays on brand
	// (one accent plus greys): the largest slice is the full accent, each smaller
	// slice a step lighter, rather than a rainbow. Sorted largest first so the
	// bar and legend read top down.
	import { weightedHoldings } from '$lib/portfolio/metrics';
	import { percent } from '$lib/format';
	import { portfolio } from '$stores/portfolio.svelte';

	const rows = $derived(
		[...weightedHoldings(portfolio.holdings)].sort((a, b) => b.weight - a.weight)
	);

	// Accent, one step lighter per rank, floored so a long tail stays visible.
	function shade(rank: number): string {
		const mix = Math.max(30, 92 - rank * 13);
		return `color-mix(in srgb, var(--primary) ${mix}%, var(--surface-2))`;
	}
</script>

{#if rows.length > 0}
	<div class="alloc">
		<div class="bar">
			{#each rows as row, i (row.ticker)}
				<div
					class="seg"
					style:width={percent(row.weight, 2)}
					style:background={shade(i)}
					title="{row.ticker} {percent(row.weight)}"
				></div>
			{/each}
		</div>
		<ul class="legend">
			{#each rows as row, i (row.ticker)}
				<li>
					<span class="dot" style:background={shade(i)}></span>
					<span class="tk">{row.ticker}</span>
					<span class="wt">{percent(row.weight)}</span>
				</li>
			{/each}
		</ul>
	</div>
{/if}

<style>
	.alloc {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.bar {
		display: flex;
		gap: 2px;
		height: 16px;
		border-radius: 999px;
		overflow: hidden;
	}
	.seg {
		height: 100%;
		min-width: 2px;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.legend li {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font-size: 13.5px;
	}
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 3px;
		flex: none;
	}
	.tk {
		font-weight: 600;
	}
	.wt {
		color: var(--text-faint);
		font-variant-numeric: tabular-nums;
	}
</style>
