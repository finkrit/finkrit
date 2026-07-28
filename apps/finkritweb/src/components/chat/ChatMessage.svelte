<script lang="ts">
	import type { ChatMessage } from '$stores/chat.svelte';

	let { message }: { message: ChatMessage } = $props();

	// Only shown on an assistant reply that actually fanned out.
	let specialists = $derived(message.specialists ?? []);
	let answers = $derived(message.specialistAnswers ?? []);

	// The pill itself is the control. A separate "show the work" link would be a
	// second thing to find, when the name of the specialist is already the thing
	// a reader wants to click.
	let open = $state<string | null>(null);

	// One specialist can be asked several sub-questions, so a pill can open onto
	// more than one exchange.
	const shown = $derived(answers.filter((a) => a.name === open));

	function toggle(name: string) {
		open = open === name ? null : name;
	}

	// A pill with nothing behind it must not look clickable. Happens when an
	// older reply predates the answers being carried, or a specialist was called
	// but never returned.
	const hasAnswer = (name: string) => answers.some((a) => a.name === name);
</script>

<!-- Floated bubbles: user right, assistant left. The wrapper clears the float
     so each message sits on its own row. An assistant reply is preceded by the
     specialists that answered it, so the fan out is visible rather than implied,
     and each one opens onto what it actually said. -->
<div class="row">
	<div class="bubble {message.role}">
		{#if specialists.length}
			<div class="pills">
				{#each specialists as name (name)}
					{#if hasAnswer(name)}
						<button
							class="pill"
							class:open={open === name}
							onclick={() => toggle(name)}
							aria-expanded={open === name}
							aria-label="{open === name ? 'Hide' : 'Show'} what the {name} specialist said"
						>
							{name}
						</button>
					{:else}
						<span class="pill flat">{name}</span>
					{/if}
				{/each}
			</div>
		{/if}

		{#if shown.length}
			<div class="work">
				{#each shown as answer, i (i)}
					<div class="exchange">
						{#if answer.question}
							<p class="asked">{answer.question}</p>
						{/if}
						<p class="said">{answer.answer}</p>
					</div>
				{/each}
				<p class="note">What the {open} specialist returned, before it was combined.</p>
			</div>
		{/if}

		<span class="text">{message.text}</span>
	</div>
</div>

<style>
	.row::after {
		content: '';
		display: block;
		clear: both;
	}
	.bubble {
		max-width: 82%;
		padding: 9px 13px;
		border-radius: 14px;
		font-size: 0.9375rem;
		line-height: 1.5;
		word-wrap: break-word;
	}
	.text {
		white-space: pre-wrap;
	}
	.bubble.user {
		float: right;
		background: var(--primary);
		color: var(--primary-contrast);
		border-bottom-right-radius: 4px;
	}
	.bubble.assistant {
		float: left;
		background: var(--surface-2);
		color: var(--text);
		border-bottom-left-radius: 4px;
	}
	.pills {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-bottom: var(--space-2);
	}
	.pill {
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.01em;
		padding: 2px 8px;
		border-radius: 999px;
		color: var(--primary-strong);
		background: var(--primary-softer);
		border: 1px solid var(--primary-soft);
	}
	button.pill {
		cursor: pointer;
	}
	button.pill:hover {
		border-color: var(--primary);
	}
	button.pill:focus-visible {
		outline: 2px solid var(--primary);
		outline-offset: 2px;
	}
	/* Inverted while open, so which pill the panel belongs to is unambiguous
	   when several are showing. */
	button.pill.open {
		background: var(--primary-strong);
		border-color: var(--primary-strong);
		color: var(--primary-contrast);
	}
	.work {
		margin-bottom: var(--space-2);
		padding: var(--space-3);
		border-radius: var(--radius-sm);
		background: var(--surface-1);
		border: 1px solid var(--border);
		font-size: 0.875rem;
	}
	.exchange + .exchange {
		margin-top: var(--space-3);
		padding-top: var(--space-3);
		border-top: 1px solid var(--border);
	}
	.asked {
		margin: 0 0 4px;
		font-weight: 600;
		color: var(--text-muted);
	}
	.said {
		margin: 0;
		white-space: pre-wrap;
	}
	.note {
		margin: var(--space-3) 0 0;
		font-size: 0.75rem;
		color: var(--text-faint);
	}
</style>
