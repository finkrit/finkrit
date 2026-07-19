<script lang="ts">
	import type { Snippet } from 'svelte';
	import LeftSidebar from './LeftSidebar.svelte';
	import ChatDock from '$components/chat/ChatDock.svelte';
	import ChatPanel from '$components/chat/ChatPanel.svelte';
	import { chat } from '$stores/chat.svelte';
	import { ui } from '$stores/ui.svelte';

	let { children }: { children: Snippet } = $props();

	// Only place the theme touches the DOM directly: CSS reads it off <html>.
	$effect(() => {
		document.documentElement.dataset.theme = ui.theme;
	});
</script>

<!--
  Three columns: [left sidebar] [center] [right chat panel].
  Whole app is one non-scrolling screen (100dvh, overflow hidden); each region
  scrolls internally. The chat dock lives at the bottom of the center while the
  panel is closed; asking a question opens the panel and hides the dock.
-->
<div class="shell">
	<LeftSidebar />

	<section class="center">
		<div class="center-body">
			{@render children()}
		</div>
		{#if !chat.open}
			<ChatDock />
		{/if}
	</section>

	{#if chat.open}
		<ChatPanel />
	{/if}
</div>

<style>
	.shell {
		display: flex;
		height: 100dvh;
		overflow: hidden;
		background: var(--bg);
	}
	.center {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.center-body {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-6);
	}
</style>
