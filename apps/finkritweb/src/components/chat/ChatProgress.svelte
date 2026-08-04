<script lang="ts">
	// What the agent is doing, while it is doing it. Replaces a bare "Thinking…"
	// with the actual fan out: which specialist was asked what, and which tools
	// ran, each settling from pending to done as its result lands.
	//
	// Steps arrive as a flat event log of starts and finishes. This folds them
	// into one row per call, keyed by call_id rather than by position, because
	// a fan out runs its specialists concurrently and they finish in whatever
	// order they finish.
	import type { ChatStep } from '$api/client';

	let { steps }: { steps: ChatStep[] } = $props();

	type Row = {
		callId: string;
		kind: 'specialist' | 'tool';
		name: string;
		detail: string;
		status: 'started' | 'finished' | 'retry';
	};

	const rows = $derived.by(() => {
		const byCall = new Map<string, Row>();
		for (const step of steps) {
			const existing = byCall.get(step.call_id);
			if (existing) {
				// A finish only ever settles the row its start created. Detail
				// lives on the start, so it is never overwritten by the finish.
				existing.status = step.status;
				continue;
			}
			byCall.set(step.call_id, {
				callId: step.call_id,
				kind: step.kind,
				name: step.name,
				detail: step.detail || describeArgs(step.args),
				status: step.status
			});
		}
		return [...byCall.values()];
	});

	// A tool has no sub-question, so its parameters stand in as the detail line.
	// portfolio_id is the opaque handle every tool takes and says nothing to a
	// reader, so it is dropped rather than shown.
	function describeArgs(args: Record<string, unknown>): string {
		return Object.entries(args ?? {})
			.filter(([key, value]) => key !== 'portfolio_id' && value !== null && value !== '')
			.map(([key, value]) => `${key.replace(/_/g, ' ')} ${value}`)
			.join(', ');
	}

	function label(row: Row): string {
		if (row.kind === 'tool') return row.name.replace(/_/g, ' ');
		return row.status === 'finished' ? `${row.name} answered` : `asking ${row.name}`;
	}
</script>

<div class="progress" role="status" aria-live="polite">
	{#if rows.length === 0}
		<div class="row">
			<span class="dot pending" aria-hidden="true"></span>
			<span class="label">Thinking…</span>
		</div>
	{/if}
	{#each rows as row (row.callId)}
		<div class="row" class:tool={row.kind === 'tool'}>
			<span
				class="dot"
				class:pending={row.status === 'started'}
				class:done={row.status === 'finished'}
				class:retry={row.status === 'retry'}
				aria-hidden="true"
			></span>
			<span class="label">{label(row)}</span>
			{#if row.detail}<span class="detail">{row.detail}</span>{/if}
		</div>
	{/each}
</div>

<style>
	.progress {
		display: flex;
		flex-direction: column;
		gap: 5px;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}
	.row {
		display: flex;
		align-items: baseline;
		gap: var(--space-2);
		min-width: 0;
	}
	/* A specialist's own tool calls sit under it, so the two grains read as a
	   hierarchy rather than one flat list. */
	.row.tool {
		padding-left: var(--space-4);
		font-size: 0.75rem;
		color: var(--text-faint);
	}
	.dot {
		flex-shrink: 0;
		width: 7px;
		height: 7px;
		border-radius: 999px;
		background: var(--border-strong);
		align-self: center;
	}
	.dot.pending {
		background: var(--primary);
		animation: pulse 1.1s ease-in-out infinite;
	}
	.dot.done {
		background: var(--positive);
		animation: none;
	}
	.dot.retry {
		background: var(--warning);
	}
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.25;
		}
	}
	.label {
		flex-shrink: 0;
	}
	.detail {
		color: var(--text-faint);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	/* Respect a reduced motion preference: the dot still changes colour, it
	   just stops pulsing. */
	@media (prefers-reduced-motion: reduce) {
		.dot.pending {
			animation: none;
		}
	}
</style>
