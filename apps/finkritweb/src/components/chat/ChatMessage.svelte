<script lang="ts">
	import type { ChatMessage } from '$stores/chat.svelte';

	let { message }: { message: ChatMessage } = $props();

	// Only shown on an assistant reply that actually fanned out.
	let specialists = $derived(message.specialists ?? []);
</script>

<!-- Floated bubbles: user right, assistant left. The wrapper clears the float
     so each message sits on its own row. An assistant reply is preceded by the
     specialists that answered it, so the fan out is visible rather than implied. -->
<div class="row">
	<div class="bubble {message.role}">
		{#if specialists.length}
			<div class="pills">
				{#each specialists as name (name)}
					<span class="pill">{name}</span>
				{/each}
			</div>
		{/if}
		<span class="text">{message.text}</span>
	</div>
</div>

<style>
	.row::after {
		content: '';
		display: block;
		clear: both;
	}
	.bubble {
		max-width: 82%;
		padding: 9px 13px;
		border-radius: 14px;
		font-size: 0.9375rem;
		line-height: 1.5;
		word-wrap: break-word;
	}
	.text {
		white-space: pre-wrap;
	}
	.bubble.user {
		float: right;
		background: var(--primary);
		color: var(--primary-contrast);
		border-bottom-right-radius: 4px;
	}
	.bubble.assistant {
		float: left;
		background: var(--surface-2);
		color: var(--text);
		border-bottom-left-radius: 4px;
	}
	.pills {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-bottom: var(--space-2);
	}
	.pill {
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.01em;
		padding: 2px 8px;
		border-radius: 999px;
		color: var(--primary-strong);
		background: var(--primary-softer);
		border: 1px solid var(--primary-soft);
	}
</style>
