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
		padding: var(--space-5);
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
		font-size: 12px;
		font-weight: 600;
		letter-spacing: 0.03em;
		text-transform: uppercase;
		color: var(--text-faint);
	}
	.value {
		font-size: clamp(20px, 9.5cqi, 30px);
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
		font-size: 12.5px;
		color: var(--text-faint);
	}
</style>
