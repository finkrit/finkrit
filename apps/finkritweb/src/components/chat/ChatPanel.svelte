<script lang="ts">
	import Icon from '$components/ui/Icon.svelte';
	import ChatInput from './ChatInput.svelte';
	import ChatMessage from './ChatMessage.svelte';
	import { chat, MAX_WIDTH, MIN_WIDTH } from '$stores/chat.svelte';

	// Auto-scroll to the newest message.
	let list = $state<HTMLElement>();
	$effect(() => {
		chat.messages.length;
		chat.sending;
		if (list) list.scrollTop = list.scrollHeight;
	});

	// Drag to resize. The panel is docked right, so width grows as the pointer
	// moves left, hence the distance from the right edge of the window. Pointer
	// capture keeps the drag alive even when the cursor outruns the handle.
	let dragging = $state(false);

	function startDrag(event: PointerEvent) {
		dragging = true;
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
		// Without this a drag across the page selects every label it passes over.
		document.body.style.userSelect = 'none';
	}

	function drag(event: PointerEvent) {
		if (!dragging) return;
		chat.setWidth(window.innerWidth - event.clientX);
	}

	function endDrag() {
		if (!dragging) return;
		dragging = false;
		document.body.style.userSelect = '';
		chat.persistWidth();
	}

	// Keyboard resizing, so the handle is not mouse only.
	function nudge(event: KeyboardEvent) {
		const step = event.shiftKey ? 64 : 16;
		if (event.key === 'ArrowLeft') chat.setWidth(chat.width + step);
		else if (event.key === 'ArrowRight') chat.setWidth(chat.width - step);
		else return;
		event.preventDefault();
		chat.persistWidth();
	}
</script>

<aside class="panel" style="width: {chat.width}px">
	<!-- A focusable separator is the ARIA window splitter pattern, which is
	     interactive by design. The linter treats every separator as static, so
	     these two rules are knowingly suppressed. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="grip"
		class:dragging
		role="separator"
		aria-orientation="vertical"
		aria-label="Resize chat panel"
		aria-valuenow={chat.width}
		aria-valuemin={MIN_WIDTH}
		aria-valuemax={MAX_WIDTH}
		tabindex="0"
		onpointerdown={startDrag}
		onpointermove={drag}
		onpointerup={endDrag}
		onpointercancel={endDrag}
		onkeydown={nudge}
	></div>
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
		/* Width is set inline from the store, so a drag can change it live and it
		   survives a reload. */
		position: relative;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-left: 1px solid var(--border);
		/* Keeps a wide default (or a wide saved width) from swallowing a small
		   screen. Re-evaluates on resize, unlike a width captured in JS once. */
		max-width: 60vw;
	}
	/* Sits on the panel's left edge, wider than the border so it is actually
	   grabbable, and only tints on hover so it stays invisible until wanted. */
	.grip {
		position: absolute;
		top: 0;
		left: -3px;
		width: 7px;
		height: 100%;
		z-index: 2;
		cursor: col-resize;
		background: transparent;
		transition: background 0.12s ease;
	}
	.grip:hover,
	.grip:focus-visible,
	.grip.dragging {
		background: var(--primary);
		outline: none;
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
		font-size: 0.875rem;
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
		font-size: 0.8125rem;
	}
	.foot {
		padding: var(--space-3) var(--space-4) var(--space-4);
		border-top: 1px solid var(--border);
	}
</style>
