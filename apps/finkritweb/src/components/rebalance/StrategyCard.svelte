<script lang="ts">
	// One strategy row of the comparison, as a selectable card. The three cards
	// share target weights and budget, so the only thing that varies is the
	// tradeoff each strategy strikes between tax cost and remaining drift,
	// which is exactly what the card leads with.
	import type { RebalancePlan } from '$api/client';
	import { money, percent } from '$lib/format';

	let {
		name,
		title,
		blurb,
		plan,
		badge,
		selected,
		maxDrift,
		onselect
	}: {
		name: string;
		title: string;
		blurb: string;
		plan: RebalancePlan;
		badge?: string;
		selected: boolean;
		maxDrift: number;
		onselect: (name: string) => void;
	} = $props();

	// Residual drift bar, scaled to the worst strategy in this comparison so
	// the three bars read against each other rather than an arbitrary ceiling.
	const driftFraction = $derived(maxDrift > 0 ? plan.residual_drift / maxDrift : 0);
</script>

<button class="card" class:selected onclick={() => onselect(name)}>
	<div class="head">
		<span class="title">{title}</span>
		{#if badge}<span class="badge">{badge}</span>{/if}
	</div>
	<p class="blurb">{blurb}</p>

	<dl class="stats">
		<div class="stat">
			<dt>Tax cost</dt>
			<dd class="cost">{money(plan.realized_gain)}</dd>
		</div>
		<div class="stat">
			<dt>Harvested</dt>
			<dd class="harvest">{plan.harvested_loss > 0 ? money(-plan.harvested_loss) : '—'}</dd>
		</div>
		<div class="stat">
			<dt>Sells</dt>
			<dd>
				{plan.sells.length}{plan.deferred.length > 0 ? ` (+${plan.deferred.length} deferred)` : ''}
			</dd>
		</div>
	</dl>

	<div class="drift">
		<div class="drift-line">
			<span class="drift-label">Residual drift</span>
			<span class="drift-value">{percent(plan.residual_drift, 2)}</span>
		</div>
		<div class="bar">
			<div class="fill" style="width: {Math.max(driftFraction * 100, plan.residual_drift > 0 ? 3 : 0)}%"></div>
		</div>
	</div>
</button>

<style>
	.card {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		text-align: left;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-4) var(--space-5);
		font-family: inherit;
		color: var(--text);
		transition:
			border-color 0.12s ease,
			box-shadow 0.12s ease;
	}
	.card:hover {
		border-color: var(--border-strong);
	}
	.card.selected {
		border-color: var(--primary);
		box-shadow: 0 0 0 1px var(--primary);
	}
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
	}
	.title {
		font-weight: 680;
		font-size: 0.9375rem;
		letter-spacing: -0.005em;
	}
	.badge {
		font-size: 0.6562rem;
		font-weight: 650;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--primary);
		background: var(--primary-softer);
		border: 1px solid var(--primary-soft);
		padding: 2px 8px;
		border-radius: 999px;
		white-space: nowrap;
	}
	.blurb {
		margin: 0;
		font-size: 0.7812rem;
		color: var(--text-muted);
		min-height: 2.6em;
	}
	.stats {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-2);
		margin: 0;
	}
	.stat dt {
		font-size: 0.6562rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--text-faint);
	}
	.stat dd {
		margin: 2px 0 0;
		font-size: 0.875rem;
		font-weight: 650;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.cost {
		color: var(--danger);
	}
	.harvest {
		color: var(--positive);
	}
	.drift-line {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 4px;
	}
	.drift-label {
		font-size: 0.6562rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--text-faint);
	}
	.drift-value {
		font-size: 0.8125rem;
		font-weight: 650;
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
		background: var(--warning);
		transition: width 0.2s ease;
	}
</style>
