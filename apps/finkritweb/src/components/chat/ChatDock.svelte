<script lang="ts">
	import ChatInput from './ChatInput.svelte';
</script>

<!-- Always-available input at the bottom of the center panel while chat is
     closed. Sending a message opens the right panel (see chat.send). -->
<div class="dock">
	<div class="dock-inner">
		<ChatInput />
	</div>
</div>

<style>
	.dock {
		flex-shrink: 0;
		padding: var(--space-4) var(--space-6) var(--space-5);
		border-top: 1px solid var(--border);
		background: var(--bg);
	}
	.dock-inner {
		max-width: 720px;
		margin: 0 auto;
	}
</style>
