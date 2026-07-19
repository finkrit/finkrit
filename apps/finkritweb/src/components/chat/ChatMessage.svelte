<script lang="ts">
	import type { ChatMessage } from '$stores/chat.svelte';

	let { message }: { message: ChatMessage } = $props();
</script>

<!-- Floated bubbles: user right, assistant left. The wrapper clears the float
     so each message sits on its own row. -->
<div class="row">
	<div class="bubble {message.role}">{message.text}</div>
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
		font-size: 13.5px;
		line-height: 1.5;
		white-space: pre-wrap;
		word-wrap: break-word;
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
</style>
