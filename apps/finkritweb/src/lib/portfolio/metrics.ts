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

export interface LotRow extends WeightedHolding {
	// Where this lot sits in the source holdings array. Grouping copies the rows,
	// so an editable cell needs the index to bind back to the real store object.
	index: number;
	shareOfPosition: number; // this lot's share of its own position, 0..1
}

export interface PositionGroup extends WeightedHolding {
	key: string;
	// The purchases that make up the position, in the order they appeared in the
	// upload. quantity, costBasis, and cost_per_share on the group are the totals
	// and the blended average across these.
	lots: LotRow[];
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

/**
 * Group tax lots into one position per instrument, keeping the lots.
 *
 * A row in the upload is one lot, not one holding, so buying the same ticker
 * three times gives three rows. Anything that talks about the PORTFOLIO rather
 * than about individual purchases (the table, the allocation bar, the position
 * count, the largest holding) has to group first, otherwise one ticker shows up
 * several times and the counts read as more positions than are actually held.
 *
 * The group's cost per share is the quantity weighted average across its lots,
 * the blended basis. That average is a display convenience and nothing more:
 * the lots stay attached, because the tax analytics need the real purchases.
 * A position can be up overall while individual lots sit underwater, and the
 * blend is exactly what hides them.
 */
export function groupByTicker(holdings: HoldingDraft[]): PositionGroup[] {
	const byKey = new Map<string, PositionGroup>();

	holdings.forEach((holding, index) => {
		// Same ticker on a different exchange or in a different currency is a
		// different instrument, so it is keyed separately.
		const key = `${holding.ticker}|${holding.exchange ?? ''}|${holding.currency ?? ''}`;
		const cb = costBasis(holding);
		const lot: LotRow = { ...holding, costBasis: cb, weight: 0, shareOfPosition: 0, index };
		const existing = byKey.get(key);
		if (!existing) {
			byKey.set(key, { ...holding, key, costBasis: cb, weight: 0, lots: [lot] });
			return;
		}
		existing.lots.push(lot);
		existing.quantity += holding.quantity;
		existing.costBasis += cb;
		existing.cost_per_share = existing.quantity > 0 ? existing.costBasis / existing.quantity : 0;
		// Show the position as first acquired, which is what the holding period
		// reads from.
		if (holding.acquired && (!existing.acquired || holding.acquired < existing.acquired)) {
			existing.acquired = holding.acquired;
		}
		// A note on any lot has to reach the collapsed row, otherwise a flagged
		// third purchase is invisible until someone expands the position.
		if (!existing.confidence_note && holding.confidence_note) {
			existing.confidence_note = holding.confidence_note;
		}
	});

	const groups = [...byKey.values()];
	const total = groups.reduce((sum, g) => sum + g.costBasis, 0);
	for (const group of groups) {
		group.weight = total > 0 ? group.costBasis / total : 0;
		for (const lot of group.lots) {
			// A lot's weight is against the portfolio, same scale as its position's,
			// so the lots of a position sum to it.
			lot.weight = total > 0 ? lot.costBasis / total : 0;
			lot.shareOfPosition = group.costBasis > 0 ? lot.costBasis / group.costBasis : 0;
		}
	}
	return groups;
}

/** Positions without their lots, for callers that only want one row per ticker. */
export function aggregateByTicker(holdings: HoldingDraft[]): WeightedHolding[] {
	return groupByTicker(holdings);
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
