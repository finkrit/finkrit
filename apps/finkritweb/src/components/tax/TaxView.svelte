<script lang="ts">
	// The tax signals dashboard: what to act on today, priced in dollars. Reads
	// the deterministic endpoint (no LLM), so the numbers are stable across
	// refreshes and identical to what the chat's tax tools would report.
	import { onMount } from 'svelte';
	import SignalCard from './SignalCard.svelte';
	import Section from '$components/portfolio/Section.svelte';
	import StatCard from '$components/ui/StatCard.svelte';
	import DownloadOverlay from '$components/ui/DownloadOverlay.svelte';
	import { api, ApiError } from '$api/client';
	import { dashData } from '$stores/dashdata.svelte';
	import { PrefetchRun } from '$stores/prefetch.svelte';
	import { money, percent, shares } from '$lib/format';

	const prefetch = new PrefetchRun();
	let error = $state<string | null>(null);
	let loading = $state(false);

	const report = $derived(dashData.tax);

	// Cached in dashData, so a revisit renders instantly with no fetch. force
	// re-runs the whole pipeline (prefetch + compute) for the refresh button.
	async function load(force = false) {
		if (dashData.tax && !force) return;
		loading = true;
		error = null;
		try {
			await prefetch.run('primary');
			dashData.tax = await api.taxSignals('primary');
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 404
					? 'No portfolio yet — upload one from the Holdings view.'
					: err instanceof ApiError
						? err.message
						: 'Could not load tax signals.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		load();
	});

	const quiet = $derived(
		report !== null &&
			report.harvest.length === 0 &&
			report.countdowns.length === 0 &&
			report.wash_sale_blocked.length === 0
	);

	function term(isLongTerm: boolean): string {
		return isLongTerm ? 'long term' : 'short term';
	}
</script>

<div class="view">
	{#if loading}
		<DownloadOverlay run={prefetch} title="Scanning your lots" computing="Checking every lot for losses, wash sales, and the long term boundary…" />
	{/if}

	<header class="head">
		<h1>Tax signals</h1>
		<div class="headside">
			{#if report}
				<span class="asof">
					as of {report.as_of} · assumes {percent(report.short_term_rate, 0)} short /
					{percent(report.long_term_rate, 0)} long term rates
				</span>
				<button class="refresh" onclick={() => load(true)} disabled={loading}>Refresh</button>
			{/if}
		</div>
	</header>

	{#if error}
		<p class="muted">{error}</p>
	{:else if report}
		<div class="hero">
			<StatCard
				label="Estimated tax saving"
				value={money(report.estimated_harvest_saving)}
				sub="if every harvest signal is taken today"
				accent
			/>
			<StatCard
				label="Harvestable loss"
				value={money(report.total_harvestable_loss)}
				sub="across {report.harvest.length} lot{report.harvest.length === 1 ? '' : 's'}, net of wash sales"
			/>
			<StatCard
				label="Nearing long term"
				value={String(report.countdowns.length)}
				sub="lots crossing the 365 day boundary soon"
			/>
		</div>

		{#if quiet}
			<div class="allclear">
				<span class="allclear-mark">✓</span>
				<div>
					<p class="allclear-title">All clear today</p>
					<p class="allclear-sub">
						No harvestable losses, no lots near the long term boundary, and no wash sale
						conflicts. Check back after the next market move.
					</p>
				</div>
			</div>
		{/if}

		{#if report.harvest.length > 0}
			<Section title="Harvest now" hint="losses ready to realize">
				<div class="cards">
					{#each report.harvest as signal (signal.lot_id)}
						<SignalCard
							tone="positive"
							chip="Harvest"
							ticker={signal.ticker}
							headline="{money(signal.unrealized_loss)} {term(signal.is_long_term)} loss is harvestable, no wash sale conflict."
							amount={money(signal.estimated_saving)}
							amountLabel="est. saving"
							details="{shares(signal.quantity)} sh · bought {signal.acquired} · basis {money(
								signal.cost_basis
							)} · now {money(signal.market_value)}"
						/>
					{/each}
				</div>
			</Section>
		{/if}

		{#if report.countdowns.length > 0}
			<Section title="Boundary countdowns" hint="the 365 day line cuts both ways">
				<div class="cards">
					{#each report.countdowns as signal (signal.lot_id)}
						{#if signal.action === 'hold'}
							<SignalCard
								tone="warning"
								chip="Hold {signal.days_until}d"
								ticker={signal.ticker}
								headline="Goes long term on {signal.transition_date}. Selling the {money(
									signal.unrealized_gain
								)} gain before then pays the short term rate."
								amount={money(signal.estimated_saving)}
								amountLabel="saved by waiting"
								details="{shares(signal.quantity)} sh · bought {signal.acquired} · now {money(
									signal.market_value
								)}"
							/>
						{:else}
							<SignalCard
								tone="warning"
								chip="Act in {signal.days_until}d"
								ticker={signal.ticker}
								headline="This {money(-signal.unrealized_gain)} loss turns long term on {signal.transition_date}. Harvested now it offsets short term gains first."
								amount={money(signal.estimated_saving)}
								amountLabel="extra offset value"
								details="{shares(signal.quantity)} sh · bought {signal.acquired} · now {money(
									signal.market_value
								)}"
							/>
						{/if}
					{/each}
				</div>
			</Section>
		{/if}

		{#if report.wash_sale_blocked.length > 0}
			<Section title="Wash sale watch" hint="losses a recent buy would forfeit">
				<div class="cards">
					{#each report.wash_sale_blocked as ticker (ticker)}
						<SignalCard
							tone="danger"
							chip="Blocked"
							{ticker}
							headline="Bought within the last 30 days. Selling at a loss now would be a wash sale and the deduction is forfeited."
						/>
					{/each}
				</div>
			</Section>
		{/if}

		<p class="foot muted">
			Savings are estimates at the assumed rates, not tax advice. Signals are computed from your
			lots in code, nothing here comes from a language model.
		</p>
	{/if}
</div>

<style>
	.view {
		max-width: 860px;
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--space-4);
		flex-wrap: wrap;
	}
	h1 {
		margin: 0;
		font-size: 1.375rem;
		font-weight: 650;
		letter-spacing: -0.01em;
	}
	.headside {
		display: flex;
		align-items: baseline;
		gap: var(--space-4);
	}
	.asof {
		font-size: 0.7812rem;
		color: var(--text-faint);
	}
	.refresh {
		background: transparent;
		border: none;
		color: var(--primary);
		font-size: 0.8125rem;
		padding: 0;
	}
	.refresh:hover:not(:disabled) {
		text-decoration: underline;
	}
	.refresh:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.hero {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-4);
	}
	@media (max-width: 900px) {
		.hero {
			grid-template-columns: 1fr;
		}
	}
	.cards {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.allclear {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-5);
	}
	.allclear-mark {
		display: grid;
		place-items: center;
		width: 40px;
		height: 40px;
		border-radius: 999px;
		background: var(--positive-soft);
		color: var(--positive);
		font-size: 1.125rem;
		font-weight: 700;
		flex-shrink: 0;
	}
	.allclear-title {
		margin: 0;
		font-weight: 650;
	}
	.allclear-sub {
		margin: 2px 0 0;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}
	.foot {
		margin: 0;
	}
	.muted {
		color: var(--text-faint);
		font-size: 0.8125rem;
	}
</style>
