<script lang="ts">
	// Portfolio level parser warnings, shown above the table so the user reviews
	// them before saving. Per row notes live on their own row instead.
	let { warnings }: { warnings: string[] } = $props();
</script>

{#if warnings.length > 0}
	<div class="warn">
		<strong>Please review before saving</strong>
		<ul>
			{#each warnings as w}<li>{w}</li>{/each}
		</ul>
	</div>
{/if}

<style>
	.warn {
		background: var(--primary-softer);
		border: 1px solid var(--primary-soft);
		border-radius: var(--radius-sm);
		padding: var(--space-3) var(--space-4);
		font-size: 13px;
	}
	.warn ul {
		margin: var(--space-1) 0 0;
		padding-left: var(--space-4);
		color: var(--text-muted);
	}
</style>
