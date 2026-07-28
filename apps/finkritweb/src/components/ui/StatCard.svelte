<script lang="ts">
	// A single headline stat: a small label, a big tabular value, an optional
	// sub line. Generic on purpose so any view can lay a row of these out.
	let {
		label,
		value,
		sub,
		accent = false
	}: { label: string; value: string; sub?: string; accent?: boolean } = $props();
</script>

<div class="stat" class:accent>
	<span class="label">{label}</span>
	<span class="value">{value}</span>
	{#if sub}<span class="sub">{sub}</span>{/if}
</div>

<style>
	.stat {
		display: flex;
		flex-direction: column;
		gap: 4px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-4);
		min-width: 0;
		/* Size the value against the card, not the viewport, so it shrinks to
		   fit when the column narrows (chat open) instead of truncating. */
		container-type: inline-size;
	}
	.stat.accent {
		background: var(--primary-softer);
		border-color: var(--primary-soft);
	}
	.label {
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.03em;
		text-transform: uppercase;
		color: var(--text-faint);
	}
	.value {
		/* Deliberately below the old ceiling. These are reference figures on a
		   dense dashboard, not a hero number, and at the larger root size they
		   were dominating the holdings they are meant to summarize. */
		font-size: clamp(17px, 7cqi, 23px);
		font-weight: 660;
		letter-spacing: -0.015em;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	/* The accent card keeps a pale tinted background, but the value stays in
	   normal ink. In a markets UI green means gains, and cost basis is a
	   neutral figure. Reserve green and red for actual P&L and return. */
	.sub {
		font-size: 0.7812rem;
		color: var(--text-faint);
	}
</style>
