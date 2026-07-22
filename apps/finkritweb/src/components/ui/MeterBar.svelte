<script lang="ts">
	// A single proportion bar. One fraction (0..1) fills a rounded track. Used
	// for a holding's weight in the table, reusable anywhere a share of a whole
	// needs a quiet inline visual.
	let {
		fraction,
		color = 'var(--primary)',
		height = 6
	}: { fraction: number; color?: string; height?: number } = $props();

	const width = $derived(`${Math.max(0, Math.min(1, fraction)) * 100}%`);
</script>

<div class="track" style:height="{height}px">
	<div class="fill" style:width style:background={color}></div>
</div>

<style>
	.track {
		width: 100%;
		background: var(--surface-2);
		border-radius: 999px;
		overflow: hidden;
	}
	.fill {
		height: 100%;
		border-radius: 999px;
		transition: width 0.2s ease;
	}
</style>
