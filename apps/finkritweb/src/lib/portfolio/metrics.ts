// Everything derivable from a parsed portfolio WITHOUT market data. Cost basis,
// weights, and a one-shot overview all come from what the upload already gave
// us (quantity, cost per share, acquired date). Prices and market value are a
// later layer that needs the registry, this file stays network free so the
// display can render the moment a file is parsed.
//
// Pure functions only, no Svelte. Components wrap these in $derived so the
// numbers recompute as the user edits, but the arithmetic lives here where it
// can be tested on its own.
import type { HoldingDraft } from '$api/client';

export interface WeightedHolding extends HoldingDraft {
	costBasis: number; // quantity * cost per share
	weight: number; // share of the portfolio's total cost basis, 0..1
}

export interface PortfolioOverview {
	count: number;
	totalCostBasis: number;
	currency: string;
	mixedCurrency: boolean; // holdings span more than one currency
	largest: WeightedHolding | null;
	earliestAcquired: string | null;
	latestAcquired: string | null;
}

export function costBasis(holding: HoldingDraft): number {
	return holding.quantity * holding.cost_per_share;
}

export function weightedHoldings(holdings: HoldingDraft[]): WeightedHolding[] {
	const total = holdings.reduce((sum, h) => sum + costBasis(h), 0);
	return holdings.map((h) => {
		const cb = costBasis(h);
		return { ...h, costBasis: cb, weight: total > 0 ? cb / total : 0 };
	});
}

export function overview(holdings: HoldingDraft[]): PortfolioOverview {
	const rows = weightedHoldings(holdings);
	const total = rows.reduce((sum, r) => sum + r.costBasis, 0);
	const currencies = new Set(holdings.map((h) => h.currency ?? 'USD'));
	// ISO dates sort correctly as plain strings, so no Date parsing needed.
	const dates = holdings.map((h) => h.acquired).filter(Boolean).sort();
	const largest = rows.reduce<WeightedHolding | null>(
		(top, r) => (top && top.costBasis >= r.costBasis ? top : r),
		null
	);
	return {
		count: holdings.length,
		totalCostBasis: total,
		currency: currencies.size === 1 ? [...currencies][0] : 'USD',
		mixedCurrency: currencies.size > 1,
		largest,
		earliestAcquired: dates[0] ?? null,
		latestAcquired: dates.at(-1) ?? null
	};
}
