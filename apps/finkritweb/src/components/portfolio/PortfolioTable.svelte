<script lang="ts">
	import HoldingRow from './HoldingRow.svelte';
	import { portfolio } from '$stores/portfolio.svelte';

	let { editable = false }: { editable?: boolean } = $props();

	function remove(index: number) {
		portfolio.holdings = portfolio.holdings.filter((_, i) => i !== index);
	}
</script>

<table class="table">
	<thead>
		<tr>
			<th>Ticker</th>
			<th class="num">Quantity</th>
			<th class="num">Cost / share</th>
			<th>Acquired</th>
			<th></th>
		</tr>
	</thead>
	<tbody>
		{#each portfolio.holdings as holding, i (i)}
			<HoldingRow {holding} {editable} onremove={() => remove(i)} />
		{/each}
	</tbody>
</table>

<style>
	.table {
		width: 100%;
		border-collapse: collapse;
	}
	th {
		text-align: left;
		padding: 0 var(--space-3) var(--space-2) 0;
		border-bottom: 1px solid var(--border-strong);
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.03em;
		text-transform: uppercase;
		color: var(--text-faint);
	}
	.num {
		text-align: left;
	}
</style>
