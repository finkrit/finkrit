<script lang="ts">
	import Icon from '$components/ui/Icon.svelte';
	import { chat } from '$stores/chat.svelte';

	// Shared by the dock (chat closed) and the panel (chat open) so there's one
	// input implementation, not two.
	let { placeholder = 'Ask about your portfolio…' }: { placeholder?: string } = $props();

	let text = $state('');

	function submit(e: Event) {
		e.preventDefault();
		const q = text;
		text = '';
		chat.send(q);
	}
</script>

<form class="input" onsubmit={submit}>
	<input type="text" bind:value={text} {placeholder} />
	<button type="submit" class="send" disabled={!text.trim() || chat.sending} aria-label="Send">
		<Icon name="send" size={16} />
	</button>
</form>

<style>
	.input {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		background: var(--surface);
		border: 1px solid var(--border-strong);
		border-radius: 999px;
		padding: 6px 6px 6px var(--space-4);
		box-shadow: var(--shadow-sm);
	}
	.input:focus-within {
		border-color: var(--primary);
	}
	input {
		flex: 1;
		min-width: 0;
		border: none;
		outline: none;
		background: transparent;
		font-size: 14px;
		color: var(--text);
	}
	.send {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		width: 32px;
		height: 32px;
		border: none;
		border-radius: 999px;
		background: var(--primary);
		color: var(--primary-contrast);
		transition: background 0.12s ease;
	}
	.send:disabled {
		background: var(--border-strong);
		cursor: default;
	}
	.send:not(:disabled):hover {
		background: var(--primary-strong);
	}
</style>
