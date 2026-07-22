<script lang="ts">
	// Orchestrator only. Owns the stage transitions and the save side effect,
	// and composes the display pieces. Everything that renders data lives in its
	// own component (summary, allocation, table, notes), so this file stays a
	// thin wiring layer rather than a screen that does everything.
	import PortfolioUpload from './PortfolioUpload.svelte';
	import PortfolioSummary from './PortfolioSummary.svelte';
	import AllocationBar from './AllocationBar.svelte';
	import HoldingsTable from './HoldingsTable.svelte';
	import ReviewNotes from './ReviewNotes.svelte';
	import Section from './Section.svelte';
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
		<div class="empty">
			<PortfolioUpload />
		</div>
	{:else}
		<div class="stack">
			<ReviewNotes warnings={portfolio.warnings} />

			<label class="name">
				Portfolio name
				<input bind:value={portfolio.name} />
			</label>

			<div class="top">
				<Section title="Overview">
					<PortfolioSummary />
				</Section>
				<Section title="Allocation" hint="by cost basis">
					<div class="panel">
						<AllocationBar />
					</div>
				</Section>
			</div>

			<Section title="Holdings">
				<HoldingsTable editable={portfolio.stage === 'review'} />
			</Section>

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
		</div>
	{/if}
</div>

<style>
	.view {
		width: 100%;
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin-bottom: var(--space-5);
	}
	h1 {
		margin: 0;
		font-size: 27px;
		font-weight: 650;
		letter-spacing: -0.015em;
	}
	.reupload {
		background: transparent;
		border: none;
		color: var(--primary);
		font-size: 14px;
	}
	.reupload:hover {
		text-decoration: underline;
	}
	.empty {
		display: flex;
		justify-content: center;
		padding-top: 7vh;
	}
	.stack {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}
	.name {
		display: block;
		font-size: 13px;
		color: var(--text-muted);
	}
	.name input {
		display: block;
		margin-top: var(--space-1);
		width: 100%;
		max-width: 360px;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		padding: 9px 12px;
		font-size: 15px;
		font-family: inherit;
	}
	.name input:focus {
		outline: none;
		border-color: var(--primary);
	}
	/* Top region uses the width: overview cards beside the allocation panel.
	   Collapses to a single column when the space gets tight (chat open, or a
	   narrow window). */
	.top {
		display: grid;
		grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
		gap: var(--space-6);
		align-items: start;
	}
	@media (max-width: 1080px) {
		.top {
			grid-template-columns: 1fr;
		}
	}
	.panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: var(--space-5);
	}
	.actions {
		margin-top: var(--space-1);
	}
	.saved {
		margin: 0;
		color: var(--positive);
		font-size: 14px;
	}
	.error {
		color: var(--danger);
		font-size: 14px;
		margin: 0;
	}
</style>
