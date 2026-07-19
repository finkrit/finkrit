<script lang="ts">
	import Icon from '$components/ui/Icon.svelte';
	import { api, ApiError } from '$api/client';
	import { portfolio } from '$stores/portfolio.svelte';
	import { acquiredOrToday } from '$utils/date';

	let error = $state<string | null>(null);
	let parsing = $state(false);

	async function onFile(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		error = null;
		parsing = true;
		try {
			const result = await api.uploadCsv(file);
			// Default a missing/epoch acquired date to today, not 1970.
			const holdings = result.holdings.map((h) => ({
				ticker: h.ticker,
				quantity: h.quantity,
				cost_per_share: h.cost_per_share,
				acquired: acquiredOrToday(h.acquired),
				exchange: h.exchange,
				currency: h.currency
			}));
			portfolio.loadParsed(result.name, holdings, result.warnings);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not read that file.';
		} finally {
			parsing = false;
		}
	}
</script>

<div class="upload">
	<label class="drop">
		<span class="ic"><Icon name="upload" size={22} /></span>
		<span class="lead">{parsing ? 'Reading your file…' : 'Upload a portfolio CSV'}</span>
		<span class="sub">Any column names/order — we'll map it. Missing dates default to today.</span>
		<input type="file" accept=".csv" onchange={onFile} disabled={parsing} />
	</label>
	{#if error}
		<p class="error">{error}</p>
	{/if}
</div>

<style>
	.upload {
		max-width: 560px;
	}
	.drop {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		text-align: center;
		padding: var(--space-6);
		background: var(--surface);
		border: 1.5px dashed var(--border-strong);
		border-radius: var(--radius);
		cursor: pointer;
		transition: border-color 0.12s ease;
	}
	.drop:hover {
		border-color: var(--primary);
	}
	.ic {
		color: var(--primary);
		margin-bottom: var(--space-1);
	}
	.lead {
		font-weight: 600;
		font-size: 15px;
	}
	.sub {
		color: var(--text-faint);
		font-size: 12.5px;
	}
	input {
		display: none;
	}
	.error {
		margin-top: var(--space-3);
		color: var(--danger);
		font-size: 13px;
	}
</style>
