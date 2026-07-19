<script lang="ts">
	let { label, value, sub }: { label: string; value: string; sub?: string } = $props();
</script>

<div class="card">
	<span class="label">{label}</span>
	<span class="value">{value}</span>
	{#if sub}<span class="sub">{sub}</span>{/if}
</div>

<style>
	.card {
		float: left;
		width: calc(25% - var(--space-3));
		margin: 0 var(--space-3) var(--space-3) 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-4);
	}
	.label {
		font-size: 11.5px;
		font-weight: 600;
		color: var(--text-faint);
	}
	.value {
		font-size: 24px;
		font-weight: 650;
		letter-spacing: -0.01em;
		font-variant-numeric: tabular-nums;
	}
	.sub {
		font-size: 11.5px;
		color: var(--text-faint);
	}
</style>
