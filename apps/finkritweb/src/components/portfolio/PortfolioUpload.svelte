<script lang="ts">
	import Icon from '$components/ui/Icon.svelte';
	import { api, ApiError } from '$api/client';
	import { portfolio } from '$stores/portfolio.svelte';
	import { acquiredOrToday } from '$utils/date';

	let error = $state<string | null>(null);
	let parsing = $state(false);
	let dragging = $state(false);
	let fileName = $state<string | null>(null);

	async function ingest(file: File) {
		error = null;
		fileName = file.name;
		parsing = true;
		try {
			const result = await api.uploadCsv(file);
			const holdings = result.holdings.map((h) => ({
				ticker: h.ticker,
				quantity: h.quantity,
				cost_per_share: h.cost_per_share,
				// A holding you own was not acquired in 1970, default a missing
				// or epoch date to today rather than showing a nonsense date.
				acquired: acquiredOrToday(h.acquired),
				exchange: h.exchange,
				currency: h.currency,
				confidence_note: h.confidence_note
			}));
			portfolio.loadParsed(result.name, holdings, result.warnings);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not read that file.';
		} finally {
			parsing = false;
		}
	}

	function onFile(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (file) ingest(file);
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		const file = e.dataTransfer?.files?.[0];
		if (file) ingest(file);
	}
</script>

<div class="upload">
	<label
		class="drop"
		class:dragging
		class:busy={parsing}
		ondragover={(e) => {
			e.preventDefault();
			dragging = true;
		}}
		ondragleave={() => (dragging = false)}
		ondrop={onDrop}
	>
		{#if parsing}
			<span class="spinner" aria-hidden="true"></span>
			<span class="lead">Reading {fileName}…</span>
			<span class="sub">Mapping your columns with AI. This takes a few seconds.</span>
		{:else}
			<span class="ic"><Icon name="upload" size={28} /></span>
			<span class="lead">Drop a portfolio CSV, or click to browse</span>
			<span class="sub">Any column names or order, we map it for you. Missing dates default to today.</span>
		{/if}
		<input type="file" accept=".csv" onchange={onFile} disabled={parsing} />
	</label>
	{#if error}
		<p class="error">{error}</p>
	{/if}
</div>

<style>
	.upload {
		width: 100%;
		max-width: 620px;
	}
	.drop {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		text-align: center;
		padding: var(--space-6) var(--space-6) calc(var(--space-6) + 4px);
		background: var(--surface);
		border: 1.5px dashed var(--border-strong);
		border-radius: var(--radius);
		cursor: pointer;
		transition:
			border-color 0.12s ease,
			background 0.12s ease;
	}
	.drop:hover {
		border-color: var(--primary);
	}
	.drop.dragging {
		border-color: var(--primary);
		background: var(--primary-softer);
	}
	.drop.busy {
		cursor: default;
		border-color: var(--primary);
		background: var(--primary-softer);
	}
	.ic {
		color: var(--primary);
		margin-bottom: var(--space-1);
	}
	.spinner {
		width: 26px;
		height: 26px;
		margin-bottom: var(--space-2);
		border: 2.5px solid var(--primary-soft);
		border-top-color: var(--primary);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.lead {
		font-weight: 600;
		font-size: 16.5px;
	}
	.sub {
		color: var(--text-faint);
		font-size: 13.5px;
	}
	input {
		display: none;
	}
	.error {
		margin-top: var(--space-3);
		color: var(--danger);
		font-size: 14px;
	}
</style>
