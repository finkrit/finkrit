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

/**
 * Collapse tax lots into one row per instrument.
 *
 * A row in the upload is one lot, not one holding, so buying the same ticker
 * three times gives three rows. Anything that talks about the PORTFOLIO rather
 * than about individual purchases (the allocation bar, the position count, the
 * largest holding) has to aggregate first, otherwise one ticker shows up as
 * several slices and the counts read as more positions than are actually held.
 *
 * Cost per share becomes the quantity weighted average across the lots, which
 * is the blended basis. The individual lots are still what the tax analytics
 * use, this is only for display.
 */
export function aggregateByTicker(holdings: HoldingDraft[]): WeightedHolding[] {
	const byTicker = new Map<string, WeightedHolding & { lots: number }>();

	for (const holding of holdings) {
		// Same ticker on a different exchange or in a different currency is a
		// different instrument, so it is keyed separately.
		const key = `${holding.ticker}|${holding.exchange ?? ''}|${holding.currency ?? ''}`;
		const cb = costBasis(holding);
		const existing = byTicker.get(key);
		if (!existing) {
			byTicker.set(key, { ...holding, costBasis: cb, weight: 0, lots: 1 });
			continue;
		}
		existing.quantity += holding.quantity;
		existing.costBasis += cb;
		existing.lots += 1;
		existing.cost_per_share = existing.quantity > 0 ? existing.costBasis / existing.quantity : 0;
		// Show the position as first acquired, which is what the holding period
		// reads from.
		if (holding.acquired && (!existing.acquired || holding.acquired < existing.acquired)) {
			existing.acquired = holding.acquired;
		}
	}

	const rows = [...byTicker.values()];
	const total = rows.reduce((sum, r) => sum + r.costBasis, 0);
	return rows.map((r) => ({ ...r, weight: total > 0 ? r.costBasis / total : 0 }));
}

export function overview(holdings: HoldingDraft[]): PortfolioOverview {
	// Aggregated, because these describe the portfolio rather than individual
	// purchases. Counting rows would report a ticker bought three times as three
	// positions, and the largest holding would be the largest single lot.
	const rows = aggregateByTicker(holdings);
	const total = rows.reduce((sum, r) => sum + r.costBasis, 0);
	const currencies = new Set(holdings.map((h) => h.currency ?? 'USD'));
	// ISO dates sort correctly as plain strings, so no Date parsing needed. Taken
	// from the lots, so the span covers the first and last purchase.
	const dates = holdings.map((h) => h.acquired).filter(Boolean).sort();
	const largest = rows.reduce<WeightedHolding | null>(
		(top, r) => (top && top.costBasis >= r.costBasis ? top : r),
		null
	);
	return {
		count: rows.length,
		totalCostBasis: total,
		currency: currencies.size === 1 ? [...currencies][0] : 'USD',
		mixedCurrency: currencies.size > 1,
		largest,
		earliestAcquired: dates[0] ?? null,
		latestAcquired: dates.at(-1) ?? null
	};
}
