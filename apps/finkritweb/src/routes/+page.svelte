<script lang="ts">
	// The middle panel. Which view shows is driven by the left sidebar (ui store),
	// not by the router -- the whole app is one screen. Add a view: a new id in
	// ui.svelte.ts, a case here, and a sidebar item.
	import PortfolioView from '$components/portfolio/PortfolioView.svelte';
	import RiskView from '$components/portfolio/RiskView.svelte';
	import TaxView from '$components/tax/TaxView.svelte';
	import RebalanceView from '$components/rebalance/RebalanceView.svelte';
	import { ui } from '$stores/ui.svelte';
</script>

{#if ui.view === 'portfolio'}
	<PortfolioView />
{:else if ui.view === 'risk'}
	<RiskView />
{:else if ui.view === 'tax'}
	<TaxView />
{:else if ui.view === 'rebalance'}
	<RebalanceView />
{/if}
