// The single portfolio's state, shared across the portfolio + risk views.
import type { HoldingDraft } from '$api/client';
import { lotExpansion } from './lots.svelte';

export type Stage = 'empty' | 'review' | 'saved';

class PortfolioState {
	stage = $state<Stage>('empty');
	name = $state('');
	holdings = $state<HoldingDraft[]>([]);
	warnings = $state<string[]>([]);

	loadParsed(name: string, holdings: HoldingDraft[], warnings: string[]) {
		this.name = name;
		this.holdings = holdings;
		this.warnings = warnings;
		this.stage = 'review';
		// Expansion is keyed by ticker, so a new upload sharing a ticker with the
		// last one would otherwise inherit its open state.
		lotExpansion.clear();
	}

	markSaved() {
		this.warnings = [];
		this.stage = 'saved';
	}

	reset() {
		this.stage = 'empty';
		this.name = '';
		this.holdings = [];
		this.warnings = [];
		lotExpansion.clear();
	}
}

export const portfolio = new PortfolioState();
