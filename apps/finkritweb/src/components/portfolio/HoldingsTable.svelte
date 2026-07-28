<script lang="ts">
	// The holdings table. One row per position, not per row of the upload, so a
	// ticker bought three times appears once with a blended cost per share and
	// expands to show the three purchases.
	//
	// Grouping copies the rows, so every editable row is handed the real store
	// object at `lot.index` rather than the copy. The inputs bind to the store
	// and the derived numbers recompute as the user types.
	import HoldingRow from './HoldingRow.svelte';
	import PositionRow from './PositionRow.svelte';
	import { groupByTicker, overview, type PositionGroup } from '$lib/portfolio/metrics';
	import { portfolio } from '$stores/portfolio.svelte';
	import { lotExpansion } from '$stores/lots.svelte';

	let { editable = false }: { editable?: boolean } = $props();

	const groups = $derived(groupByTicker(portfolio.holdings));
	const currency = $derived(overview(portfolio.holdings).currency);

	// Editing a collapsed position would hide its inputs, so review starts them
	// open. Everywhere else they start collapsed. Positions the user has actually
	// clicked keep their choice either way, the store holds only those.
	const startsOpen = $derived(editable);
	const isOpen = (group: PositionGroup) => lotExpansion.isOpen(group.key, startsOpen);

	// Only positions with more than one lot have anything to show, so they are
	// the only ones the expand all control touches, and it hides entirely when
	// no position was bought twice.
	const expandable = $derived(groups.filter((group) => group.lots.length > 1));
	const allOpen = $derived(lotExpansion.allOpen(expandable.map((g) => g.key), startsOpen));

	function toggleAll() {
		// Anything short of every position being open counts as closed, so a half
		// open table expands rather than collapsing what is already showing.
		lotExpansion.setAll(expandable.map((g) => g.key), !allOpen);
	}

	function remove(index: number) {
		portfolio.holdings = portfolio.holdings.filter((_, i) => i !== index);
	}
</script>

<table class="table">
	<thead>
		<tr>
			<th>
				<span>Ticker</span>
				{#if expandable.length}
					<!-- Sits directly above the per position chevrons, in the same
					     column, so the control reads as applying to all of them. -->
					<button class="all" onclick={toggleAll} aria-expanded={allOpen}>
						<svg class="chevron" class:open={allOpen} viewBox="0 0 10 10" aria-hidden="true">
							<path d="M3 1.5 L7 5 L3 8.5" fill="none" stroke="currentColor" stroke-width="1.6"
								stroke-linecap="round" stroke-linejoin="round" />
						</svg>
						{allOpen ? 'Collapse all' : 'Expand all'}
					</button>
				{/if}
			</th>
			<th class="w">Weight</th>
			<th class="num">Quantity</th>
			<th class="num">Cost / share</th>
			<th class="num">Cost basis</th>
			<th>Acquired</th>
			{#if editable}<th></th>{/if}
		</tr>
	</thead>
	<tbody>
		{#each groups as group (group.key)}
			{#if group.lots.length === 1}
				<!-- Bought once, so the position and the lot are the same thing and
				     there is nothing to expand. -->
				<HoldingRow
					holding={portfolio.holdings[group.lots[0].index]}
					weight={group.weight}
					costBasis={group.costBasis}
					{currency}
					{editable}
					onremove={() => remove(group.lots[0].index)}
				/>
			{:else}
				<PositionRow
					{group}
					{currency}
					{editable}
					expanded={isOpen(group)}
					ontoggle={() => lotExpansion.toggle(group.key, startsOpen)}
				/>
				{#if isOpen(group)}
					{#each group.lots as lot, n (lot.index)}
						<HoldingRow
							holding={portfolio.holdings[lot.index]}
							weight={lot.weight}
							costBasis={lot.costBasis}
							shareOfPosition={lot.shareOfPosition}
							lotLabel="Lot {n + 1}"
							{currency}
							{editable}
							onremove={() => remove(lot.index)}
						/>
					{/each}
				{/if}
			{/if}
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
		font-size: 0.75rem;
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
	.all {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		margin-left: var(--space-3);
		padding: 0;
		background: transparent;
		border: none;
		/* Inherits the header's uppercase and letter spacing, so it reads as part
		   of the header rather than a control dropped into it. */
		font: inherit;
		letter-spacing: inherit;
		text-transform: inherit;
		color: var(--primary-strong);
		cursor: pointer;
		border-radius: var(--radius-xs);
	}
	.all:hover {
		color: var(--primary);
	}
	.all:focus-visible {
		outline: 2px solid var(--primary);
		outline-offset: 3px;
	}
	.chevron {
		width: 9px;
		height: 9px;
		flex: none;
		transition: transform 0.15s ease;
	}
	.chevron.open {
		transform: rotate(90deg);
	}
</style>
