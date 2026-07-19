<script lang="ts">
	// The middle panel. Which view shows is driven by the left sidebar (ui store),
	// not by the router -- the whole app is one screen. Add a view: a new id in
	// ui.svelte.ts, a case here, and a sidebar item.
	import PortfolioView from '$components/portfolio/PortfolioView.svelte';
	import RiskView from '$components/portfolio/RiskView.svelte';
	import { ui } from '$stores/ui.svelte';
</script>

{#if ui.view === 'portfolio'}
	<PortfolioView />
{:else if ui.view === 'risk'}
	<RiskView />
{/if}
