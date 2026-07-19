// The single portfolio's state, shared across the portfolio + risk views.
import type { HoldingDraft } from '$api/client';

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
	}
}

export const portfolio = new PortfolioState();
