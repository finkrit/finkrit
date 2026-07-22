<script lang="ts">
	// The holdings table. Iterates the real store holdings so the edit inputs
	// bind straight to them, and pairs each with its derived weight and cost
	// basis (same order) for display. Both recompute live as the user edits.
	import HoldingRow from './HoldingRow.svelte';
	import { weightedHoldings, overview } from '$lib/portfolio/metrics';
	import { portfolio } from '$stores/portfolio.svelte';

	let { editable = false }: { editable?: boolean } = $props();

	const weighted = $derived(weightedHoldings(portfolio.holdings));
	const currency = $derived(overview(portfolio.holdings).currency);

	function remove(index: number) {
		portfolio.holdings = portfolio.holdings.filter((_, i) => i !== index);
	}
</script>

<table class="table">
	<thead>
		<tr>
			<th>Ticker</th>
			<th class="w">Weight</th>
			<th class="num">Quantity</th>
			<th class="num">Cost / share</th>
			<th class="num">Cost basis</th>
			<th>Acquired</th>
			{#if editable}<th></th>{/if}
		</tr>
	</thead>
	<tbody>
		{#each portfolio.holdings as holding, i (i)}
			<HoldingRow
				{holding}
				weight={weighted[i].weight}
				costBasis={weighted[i].costBasis}
				{currency}
				{editable}
				onremove={() => remove(i)}
			/>
		{/each}
	</tbody>
</table>

<style>
	.table {
		width: 100%;
		border-collapse: collapse;
	}
	th {
		padding: 0 var(--space-3) var(--space-3) 0;
		border-bottom: 1px solid var(--border-strong);
		font-size: 12px;
		font-weight: 600;
		letter-spacing: 0.03em;
		text-transform: uppercase;
		color: var(--text-faint);
		text-align: left;
	}
	.num {
		text-align: right;
	}
	.w {
		width: 180px;
	}
</style>
