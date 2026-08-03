<script lang="ts">
	// The visible download: an overlay over the view with a live progress bar
	// and one chip per ticker, lighting up as each download lands. Driven by a
	// PrefetchRun. Once every ticker has reported, the copy flips to the
	// compute stage (the math runs after the data is warm), so the overlay
	// never sits silent while work is still happening.
	import type { PrefetchRun } from '$stores/prefetch.svelte';

	let {
		run,
		title,
		computing = 'Crunching the numbers…'
	}: {
		run: PrefetchRun;
		title: string;
		computing?: string;
	} = $props();

	const downloading = $derived(run.total === 0 || run.done < run.total);
	const fraction = $derived(run.total > 0 ? run.done / run.total : 0);
</script>

<div class="backdrop" role="status" aria-live="polite">
	<div class="panel">
		<div class="head">
			<span class="spinner" aria-hidden="true"></span>
			<div>
				<p class="title">{title}</p>
				<p class="sub">
					{#if downloading}
						{#if run.total > 0}
							Downloading market data · {run.done} of {run.total}
						{:else}
							Contacting the market data provider…
						{/if}
					{:else}
						{computing}
					{/if}
				</p>
			</div>
		</div>

		{#if run.total > 0}
			<div class="bar">
				<div class="fill" style="width: {Math.max(fraction * 100, 4)}%"></div>
			</div>
			<div class="chips">
				{#each run.tickers as ticker (ticker)}
					<span
						class="chip"
						class:ready={run.status[ticker] === 'ready'}
						class:failed={run.status[ticker] === 'error'}>{ticker}</span
					>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		display: grid;
		place-items: center;
		background: color-mix(in srgb, var(--bg) 62%, transparent);
		backdrop-filter: blur(3px);
	}
	.panel {
		width: min(460px, calc(100vw - 48px));
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow-md);
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.head {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}
	.spinner {
		flex-shrink: 0;
		width: 22px;
		height: 22px;
		border-radius: 999px;
		border: 2.5px solid var(--primary-soft);
		border-top-color: var(--primary);
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.title {
		margin: 0;
		font-weight: 650;
		font-size: 0.9375rem;
	}
	.sub {
		margin: 2px 0 0;
		font-size: 0.8125rem;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}
	.bar {
		height: 6px;
		border-radius: 999px;
		background: var(--surface-2);
		overflow: hidden;
	}
	.fill {
		height: 100%;
		border-radius: 999px;
		background: var(--primary);
		transition: width 0.25s ease;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.chip {
		font-size: 0.6875rem;
		font-weight: 650;
		letter-spacing: 0.03em;
		padding: 2px 8px;
		border-radius: 999px;
		color: var(--text-faint);
		background: var(--surface-2);
		border: 1px solid var(--border);
		transition:
			color 0.15s ease,
			background 0.15s ease;
	}
	.chip.ready {
		color: var(--positive);
		background: var(--positive-soft);
		border-color: transparent;
	}
	.chip.failed {
		color: var(--danger);
		background: var(--danger-soft);
		border-color: transparent;
	}
</style>
