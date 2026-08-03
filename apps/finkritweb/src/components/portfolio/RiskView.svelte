<script lang="ts">
	import { onMount } from 'svelte';
	import RiskCard from './RiskCard.svelte';
	import DownloadOverlay from '$components/ui/DownloadOverlay.svelte';
	import { api, ApiError } from '$api/client';
	import { dashData } from '$stores/dashdata.svelte';
	import { PrefetchRun } from '$stores/prefetch.svelte';

	const prefetch = new PrefetchRun();
	let error = $state<string | null>(null);
	let loading = $state(false);

	const report = $derived(dashData.risk);

	// Cached in dashData: a revisit renders instantly, force refetches.
	async function load(force = false) {
		if (dashData.risk && !force) return;
		loading = true;
		error = null;
		try {
			await prefetch.run('primary');
			dashData.risk = await api.report('primary', 'core');
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 404
					? 'No portfolio yet — upload one from the Holdings view.'
					: err instanceof ApiError
						? err.message
						: 'Could not load risk.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		load();
	});

	const pct = (v: number | null) => (v === null ? '—' : `${(v * 100).toFixed(2)}%`);
	const num = (v: number | null) => (v === null ? '—' : v.toFixed(2));
</script>

<div class="view">
	{#if loading}
		<DownloadOverlay run={prefetch} title="Computing risk" computing="Running the risk metrics over the lookback window…" />
	{/if}

	<div class="head">
		<h1>Risk</h1>
		{#if report}
			<button class="refresh" onclick={() => load(true)} disabled={loading}>Refresh</button>
		{/if}
	</div>

	{#if error}
		<p class="muted">{error}</p>
	{:else if report}
		<div class="cards">
			<RiskCard label="Volatility" value={pct(report.volatility)} sub="annualized" />
			<RiskCard
				label="Value at Risk"
				value={pct(report.value_at_risk)}
				sub="{(report.params.confidence * 100).toFixed(0)}% {report.params.var_method}"
			/>
			<RiskCard label="Beta" value={num(report.beta)} sub="vs {report.params.benchmark_ticker ?? '—'}" />
			<RiskCard label="Max drawdown" value={pct(report.max_drawdown)} sub="over lookback" />
		</div>
		<p class="foot muted">
			As of {report.params.as_of} · {report.params.interval} · {report.params.return_method} returns
		</p>
	{/if}
</div>

<style>
	.view {
		max-width: 760px;
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin-bottom: var(--space-5);
	}
	h1 {
		margin: 0;
		font-size: 1.375rem;
		font-weight: 650;
		letter-spacing: -0.01em;
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
	.cards::after {
		content: '';
		display: block;
		clear: both;
	}
	.foot {
		margin-top: var(--space-3);
	}
	.muted {
		color: var(--text-faint);
		font-size: 0.8125rem;
	}
</style>
