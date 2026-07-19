<script lang="ts">
	import PortfolioUpload from './PortfolioUpload.svelte';
	import PortfolioTable from './PortfolioTable.svelte';
	import Button from '$components/ui/Button.svelte';
	import { api, ApiError } from '$api/client';
	import { portfolio } from '$stores/portfolio.svelte';

	let saving = $state(false);
	let error = $state<string | null>(null);

	async function save() {
		saving = true;
		error = null;
		try {
			await api.registerPortfolio(portfolio.name, portfolio.holdings);
			portfolio.markSaved();
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not save.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="view">
	<header class="head">
		<h1>Portfolio</h1>
		{#if portfolio.stage !== 'empty'}
			<button class="reupload" onclick={() => portfolio.reset()}>Upload a different file</button>
		{/if}
	</header>

	{#if portfolio.stage === 'empty'}
		<PortfolioUpload />
	{:else}
		{#if portfolio.warnings.length > 0}
			<div class="warn">
				<strong>Please review:</strong>
				<ul>
					{#each portfolio.warnings as w}<li>{w}</li>{/each}
				</ul>
			</div>
		{/if}

		<label class="name">
			Name
			<input bind:value={portfolio.name} />
		</label>

		<PortfolioTable editable={portfolio.stage === 'review'} />

		{#if error}<p class="error">{error}</p>{/if}

		{#if portfolio.stage === 'review'}
			<div class="actions">
				<Button onclick={save} disabled={saving || portfolio.holdings.length === 0}>
					{saving ? 'Saving…' : 'Save portfolio'}
				</Button>
			</div>
		{:else}
			<p class="saved">✓ Saved. Ask about its risk in chat, or open the Risk view.</p>
		{/if}
	{/if}
</div>

<style>
	.view {
		max-width: 760px;
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin-bottom: var(--space-5);
	}
	h1 {
		margin: 0;
		font-size: 22px;
		font-weight: 650;
		letter-spacing: -0.01em;
	}
	.reupload {
		background: transparent;
		border: none;
		color: var(--primary);
		font-size: 13px;
	}
	.reupload:hover {
		text-decoration: underline;
	}
	.warn {
		background: var(--primary-softer);
		border: 1px solid var(--primary-soft);
		border-radius: var(--radius-sm);
		padding: var(--space-3) var(--space-4);
		margin-bottom: var(--space-4);
		font-size: 13px;
	}
	.warn ul {
		margin: var(--space-1) 0 0;
		padding-left: var(--space-4);
		color: var(--text-muted);
	}
	.name {
		display: block;
		font-size: 12px;
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}
	.name input {
		display: block;
		margin-top: var(--space-1);
		width: 100%;
		max-width: 340px;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		padding: 7px 10px;
		font-size: 14px;
		font-family: inherit;
	}
	.name input:focus {
		outline: none;
		border-color: var(--primary);
	}
	.actions {
		margin-top: var(--space-5);
	}
	.saved {
		margin-top: var(--space-5);
		color: var(--positive);
		font-size: 13px;
	}
	.error {
		color: var(--danger);
		font-size: 13px;
		margin-top: var(--space-3);
	}
</style>
