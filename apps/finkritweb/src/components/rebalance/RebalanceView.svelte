<script lang="ts">
	// The drift budget view: what rebalancing costs in tax under each of the
	// three named strategies, side by side. The menu is fixed in code on the
	// server (full / band_edge / partial_fill), the view only chooses the shared
	// inputs: objective, gain budget, tolerance. Deterministic endpoint, no LLM.
	import { onMount } from 'svelte';
	import StrategyCard from './StrategyCard.svelte';
	import Section from '$components/portfolio/Section.svelte';
	import DownloadOverlay from '$components/ui/DownloadOverlay.svelte';
	import { api, ApiError } from '$api/client';
	import { dashData } from '$stores/dashdata.svelte';
	import { PrefetchRun } from '$stores/prefetch.svelte';
	import { money, percent } from '$lib/format';

	type StrategyName = 'full' | 'band_edge' | 'partial_fill';

	const STRATEGY_COPY: Record<StrategyName, { title: string; blurb: string }> = {
		full: {
			title: 'Full rebalance',
			blurb: 'Sell every overweight all the way to its target weight.'
		},
		band_edge: {
			title: 'To band edge',
			blurb: 'Sell only the excess beyond the tolerance band. Less selling, more drift kept.'
		},
		partial_fill: {
			title: 'Partial fill',
			blurb: 'Scale budget-breaching sells down to spend the gain budget to the dollar.'
		}
	};

	const prefetch = new PrefetchRun();
	let error = $state<string | null>(null);
	let loading = $state(false);
	let selected = $state<StrategyName>('full');

	const compare = $derived(dashData.compare);

	// Inputs. Budget empty string means unlimited (the parameter is omitted).
	let objective = $state<'min_variance' | 'max_sharpe'>('min_variance');
	let budgetText = $state('');
	let tolerancePct = $state(2);

	// onMount, not $effect: load() reads the form inputs synchronously, so an
	// effect would track them and refire the comparison on every keystroke.
	// The Compare button is the explicit trigger; mount fills first paint from
	// the dashData cache when a comparison already ran this session.
	onMount(() => {
		if (!dashData.compare) load();
	});

	async function load() {
		loading = true;
		error = null;
		try {
			const gainBudget = budgetText.trim() === '' ? undefined : Number(budgetText);
			if (gainBudget !== undefined && (!Number.isFinite(gainBudget) || gainBudget < 0)) {
				error = 'Gain budget must be a positive dollar amount, or empty for unlimited.';
				return;
			}
			// Warm the price caches first (visible progress), then compare.
			// Cache-warm this finishes in one round trip with every chip green.
			await prefetch.run('primary');
			dashData.compare = await api.rebalanceCompare('primary', {
				objective,
				gainBudget,
				tolerance: tolerancePct / 100
			});
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 404
					? 'No portfolio yet — upload one from the Holdings view.'
					: err instanceof ApiError
						? err.message
						: 'Could not run the comparison.';
		} finally {
			loading = false;
		}
	}

	const strategyNames: StrategyName[] = ['full', 'band_edge', 'partial_fill'];

	const maxDrift = $derived(
		compare ? Math.max(...strategyNames.map((n) => compare!.strategies[n].residual_drift)) : 0
	);

	// Badges computed against the other rows: the cheapest tax bill and the
	// tightest tracking, the two poles of the tradeoff the menu exists to show.
	const cheapest = $derived.by(() => {
		if (!compare) return null;
		return strategyNames.reduce((a, b) =>
			compare!.strategies[a].realized_gain <= compare!.strategies[b].realized_gain ? a : b
		);
	});
	const tightest = $derived.by(() => {
		if (!compare) return null;
		return strategyNames.reduce((a, b) =>
			compare!.strategies[a].residual_drift <= compare!.strategies[b].residual_drift ? a : b
		);
	});

	const plan = $derived(compare?.strategies[selected] ?? null);
</script>

<div class="view">
	<header class="head">
		<h1>Rebalance</h1>
		{#if compare}
			<span class="asof">as of {compare.as_of} · {compare.method} lot selection · proposals only</span>
		{/if}
	</header>

	<form
		class="controls"
		onsubmit={(e) => {
			e.preventDefault();
			load();
		}}
	>
		<label>
			<span>Objective</span>
			<select bind:value={objective}>
				<option value="min_variance">Minimum variance</option>
				<option value="max_sharpe">Maximum Sharpe</option>
			</select>
		</label>
		<label>
			<span>Gain budget ($)</span>
			<input type="text" inputmode="decimal" placeholder="unlimited" bind:value={budgetText} />
		</label>
		<label>
			<span>Tolerance (%)</span>
			<input type="number" min="0.5" max="20" step="0.5" bind:value={tolerancePct} />
		</label>
		<button type="submit" class="run" disabled={loading}>
			{loading ? 'Running…' : 'Compare'}
		</button>
	</form>

	{#if loading}
		<DownloadOverlay run={prefetch} title="Running the comparison" computing="Solving the target weights, then pricing all three strategies against your lots…" />
	{/if}

	{#if error}
		<p class="muted">{error}</p>
	{:else if compare}
		<div class="grid">
			{#each strategyNames as name (name)}
				<StrategyCard
					{name}
					title={STRATEGY_COPY[name].title}
					blurb={STRATEGY_COPY[name].blurb}
					plan={compare.strategies[name]}
					badge={name === cheapest && name === tightest
						? 'Best both ways'
						: name === cheapest
							? 'Lowest tax'
							: name === tightest
								? 'Tightest tracking'
								: undefined}
					selected={selected === name}
					{maxDrift}
					onselect={(n) => (selected = n as StrategyName)}
				/>
			{/each}
		</div>

		{#if plan}
			<Section
				title="{STRATEGY_COPY[selected].title} — sells"
				hint="sell side only, proceeds fund the underweight buys"
			>
				{#if plan.sells.length === 0}
					<p class="muted">
						No sells under this strategy{compare.gain_budget !== null
							? ' at this gain budget'
							: ''}. Everything is inside tolerance.
					</p>
				{:else}
					<div class="tablewrap">
						<table>
							<thead>
								<tr>
									<th>Ticker</th>
									<th class="num">Sell</th>
									<th class="num">Executes</th>
									<th class="num">Realized gain</th>
									<th class="num">Short term</th>
									<th class="num">Long term</th>
									<th class="num">Lots</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								{#each plan.sells as sell (sell.ticker)}
									<tr>
										<td class="ticker">{sell.ticker}</td>
										<td class="num">{money(sell.sell_value)}</td>
										<td class="num">{money(sell.executed_value)}</td>
										<td class="num" class:gain={sell.realized_gain > 0} class:loss={sell.realized_gain < 0}>
											{money(sell.realized_gain)}
										</td>
										<td class="num">{money(sell.short_term_gain)}</td>
										<td class="num">{money(sell.long_term_gain)}</td>
										<td class="num">{sell.lots_touched}</td>
										<td class="flags">
											{#if sell.is_harvest}<span class="flag harvest">harvest</span>{/if}
											{#if sell.is_partial}<span class="flag partial">partial</span>{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}

				{#if plan.deferred.length > 0}
					<p class="deferred">
						Deferred by the gain budget: <strong>{plan.deferred.join(', ')}</strong>. A bigger
						budget unlocks these next.
					</p>
				{/if}
			</Section>

			<Section title="Shared target" hint="objective: {compare.objective === 'min_variance' ? 'minimum variance' : 'maximum Sharpe'}">
				<div class="weights">
					{#each Object.entries(compare.target_weights).sort((a, b) => b[1] - a[1]) as [ticker, weight] (ticker)}
						<span class="weight"><strong>{ticker}</strong> {percent(weight, 1)}</span>
					{/each}
				</div>
			</Section>
		{/if}

		<p class="foot muted">{compare.note}</p>
	{/if}
</div>

<style>
	.view {
		max-width: 980px;
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
	.asof {
		font-size: 0.7812rem;
		color: var(--text-faint);
	}
	.controls {
		display: flex;
		align-items: flex-end;
		gap: var(--space-4);
		flex-wrap: wrap;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-4) var(--space-5);
	}
	.controls label {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--text-faint);
	}
	.controls select,
	.controls input {
		font-family: inherit;
		font-size: 0.875rem;
		color: var(--text);
		background: var(--bg);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		padding: 7px 10px;
		width: 160px;
	}
	.controls select:focus,
	.controls input:focus {
		outline: none;
		border-color: var(--primary);
	}
	.run {
		background: var(--primary);
		color: var(--primary-contrast);
		border: none;
		border-radius: var(--radius-sm);
		padding: 8px 18px;
		font-size: 0.875rem;
		font-weight: 600;
	}
	.run:hover:not(:disabled) {
		background: var(--primary-strong);
	}
	.run:disabled {
		opacity: 0.6;
		cursor: default;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-4);
	}
	@media (max-width: 960px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}
	.tablewrap {
		overflow-x: auto;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8125rem;
	}
	th {
		text-align: left;
		font-size: 0.6562rem;
		font-weight: 650;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--text-faint);
		padding: 10px var(--space-4);
		border-bottom: 1px solid var(--border);
		white-space: nowrap;
	}
	td {
		padding: 10px var(--space-4);
		border-bottom: 1px solid var(--border);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	tbody tr:last-child td {
		border-bottom: none;
	}
	th.num,
	td.num {
		text-align: right;
	}
	.ticker {
		font-weight: 650;
	}
	.gain {
		color: var(--danger);
	}
	.loss {
		color: var(--positive);
	}
	.flags {
		display: flex;
		gap: 6px;
	}
	.flag {
		font-size: 0.6562rem;
		font-weight: 650;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		padding: 1px 7px;
		border-radius: 999px;
	}
	.flag.harvest {
		color: var(--positive);
		background: var(--positive-soft);
	}
	.flag.partial {
		color: var(--warning);
		background: var(--warning-soft);
	}
	.deferred {
		margin: var(--space-3) 0 0;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}
	.weights {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-4);
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-4) var(--space-5);
		font-size: 0.8125rem;
		font-variant-numeric: tabular-nums;
	}
	.weight strong {
		font-weight: 650;
	}
	.foot {
		margin: 0;
	}
	.muted {
		color: var(--text-faint);
		font-size: 0.8125rem;
	}
</style>
