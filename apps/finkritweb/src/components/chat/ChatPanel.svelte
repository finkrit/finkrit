<script lang="ts">
	import Icon from '$components/ui/Icon.svelte';
	import ChatInput from './ChatInput.svelte';
	import ChatMessage from './ChatMessage.svelte';
	import { chat } from '$stores/chat.svelte';

	// Auto-scroll to the newest message.
	let list = $state<HTMLElement>();
	$effect(() => {
		chat.messages.length;
		chat.sending;
		if (list) list.scrollTop = list.scrollHeight;
	});
</script>

<aside class="panel">
	<header class="head">
		<span class="title"><Icon name="chat" size={16} /> Chat</span>
		<button class="close" onclick={() => chat.close()} aria-label="Close chat">
			<Icon name="close" size={16} />
		</button>
	</header>

	<div class="messages" bind:this={list}>
		{#each chat.messages as message, i (i)}
			<ChatMessage {message} />
		{/each}
		{#if chat.sending}
			<div class="thinking">Thinking…</div>
		{/if}
	</div>

	<div class="foot">
		<ChatInput placeholder="Reply…" />
	</div>
</aside>

<style>
	.panel {
		flex-shrink: 0;
		width: 384px;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-left: 1px solid var(--border);
	}
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-4) var(--space-4) var(--space-3);
		border-bottom: 1px solid var(--border);
	}
	.title {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font-weight: 600;
		font-size: 14px;
	}
	.close {
		display: inline-flex;
		background: transparent;
		border: none;
		color: var(--text-faint);
		padding: 4px;
		border-radius: var(--radius-xs);
	}
	.close:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.messages {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.thinking {
		color: var(--text-faint);
		font-size: 13px;
	}
	.foot {
		padding: var(--space-3) var(--space-4) var(--space-4);
		border-top: 1px solid var(--border);
	}
</style>
