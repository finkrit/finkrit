<script lang="ts">
	import SidebarSection from './SidebarSection.svelte';
	import SidebarItem from './SidebarItem.svelte';
	import Icon from '$components/ui/Icon.svelte';
	import { ui } from '$stores/ui.svelte';
</script>

<aside class="sidebar">
	<div class="brand">finkrit</div>

	<nav class="nav">
		<SidebarSection title="Portfolio" open>
			<SidebarItem label="Holdings" icon="holdings" view="portfolio" />
			<SidebarItem label="Risk" icon="risk" view="risk" />
		</SidebarSection>

		<SidebarSection title="Coming soon">
			<SidebarItem label="Optimization" icon="lock" disabled />
			<SidebarItem label="Tax-loss harvesting" icon="lock" disabled />
		</SidebarSection>
	</nav>

	<button class="theme-toggle" onclick={() => ui.toggleTheme()}>
		<Icon name={ui.theme === 'dark' ? 'sun' : 'moon'} size={15} />
		<span>{ui.theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
	</button>
</aside>

<style>
	.sidebar {
		flex-shrink: 0;
		width: 236px;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-right: 1px solid var(--border);
	}
	.brand {
		font-size: 17px;
		font-weight: 650;
		letter-spacing: -0.01em;
		padding: var(--space-5) var(--space-5) var(--space-4);
	}
	.nav {
		flex: 1;
		overflow-y: auto;
		padding: 0 var(--space-3) var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.theme-toggle {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin: var(--space-2) var(--space-3) var(--space-3);
		padding: 8px var(--space-2);
		background: transparent;
		border: none;
		border-top: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		font-size: 13px;
	}
	.theme-toggle:hover {
		background: var(--surface-2);
		color: var(--text);
	}
</style>
