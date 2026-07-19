<script lang="ts">
	import RiskCard from './RiskCard.svelte';
	import { api, ApiError, type PortfolioRiskReport } from '$api/client';

	let report = $state<PortfolioRiskReport | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);

	$effect(() => {
		load();
	});

	async function load() {
		loading = true;
		error = null;
		try {
			report = await api.report('primary', 'core');
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

	const pct = (v: number | null) => (v === null ? '—' : `${(v * 100).toFixed(2)}%`);
	const num = (v: number | null) => (v === null ? '—' : v.toFixed(2));
</script>

<div class="view">
	<h1>Risk</h1>

	{#if loading}
		<p class="muted">Loading…</p>
	{:else if error}
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
	h1 {
		margin: 0 0 var(--space-5);
		font-size: 22px;
		font-weight: 650;
		letter-spacing: -0.01em;
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
		font-size: 13px;
	}
</style>
