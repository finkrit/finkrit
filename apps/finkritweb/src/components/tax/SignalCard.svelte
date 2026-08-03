<script lang="ts">
	// One actionable signal: who (ticker), what to do (chip), what it is worth
	// (amount), and the lot facts that justify it (details). The shell is shared
	// across harvest, countdown, and wash sale rows so the whole view reads as
	// one system; only tone and copy differ.
	let {
		tone,
		chip,
		ticker,
		headline,
		amount,
		amountLabel,
		details
	}: {
		tone: 'positive' | 'warning' | 'danger';
		chip: string;
		ticker: string;
		headline: string;
		amount?: string;
		amountLabel?: string;
		details?: string;
	} = $props();
</script>

<div class="card {tone}">
	<div class="body">
		<div class="top">
			<span class="ticker">{ticker}</span>
			<span class="chip {tone}">{chip}</span>
		</div>
		<p class="headline">{headline}</p>
		{#if details}<p class="details">{details}</p>{/if}
	</div>
	{#if amount}
		<div class="amount-block">
			<span class="amount {tone}">{amount}</span>
			{#if amountLabel}<span class="amount-label">{amountLabel}</span>{/if}
		</div>
	{/if}
</div>

<style>
	.card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		background: var(--surface);
		border: 1px solid var(--border);
		border-left-width: 3px;
		border-radius: var(--radius);
		padding: var(--space-4) var(--space-5);
	}
	.card.positive {
		border-left-color: var(--positive);
	}
	.card.warning {
		border-left-color: var(--warning);
	}
	.card.danger {
		border-left-color: var(--danger);
	}
	.body {
		min-width: 0;
	}
	.top {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: 2px;
	}
	.ticker {
		font-weight: 680;
		font-size: 0.9375rem;
		letter-spacing: 0.01em;
	}
	.chip {
		font-size: 0.6875rem;
		font-weight: 650;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		padding: 2px 8px;
		border-radius: 999px;
		white-space: nowrap;
	}
	.chip.positive {
		color: var(--positive);
		background: var(--positive-soft);
	}
	.chip.warning {
		color: var(--warning);
		background: var(--warning-soft);
	}
	.chip.danger {
		color: var(--danger);
		background: var(--danger-soft);
	}
	.headline {
		margin: 0;
		font-size: 0.875rem;
		color: var(--text);
	}
	.details {
		margin: 2px 0 0;
		font-size: 0.7812rem;
		color: var(--text-faint);
		font-variant-numeric: tabular-nums;
	}
	.amount-block {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		flex-shrink: 0;
	}
	.amount {
		font-size: 1.125rem;
		font-weight: 680;
		letter-spacing: -0.01em;
		font-variant-numeric: tabular-nums;
	}
	.amount.positive {
		color: var(--positive);
	}
	.amount.warning {
		color: var(--warning);
	}
	.amount.danger {
		color: var(--danger);
	}
	.amount-label {
		font-size: 0.6875rem;
		color: var(--text-faint);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
</style>
