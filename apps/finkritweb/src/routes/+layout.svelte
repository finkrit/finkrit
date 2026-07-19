<script lang="ts">
	import '$theme/theme.css';
	import AppShell from '$components/layout/AppShell.svelte';

	let { children } = $props();
</script>

<AppShell>
	{@render children()}
</AppShell>
