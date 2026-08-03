// Session cache for the deterministic dashboard payloads.
//
// Each view used to hold its result in component state, which dies when the
// sidebar switches views, so every visit refetched and the app looked like it
// was downloading the same data over and over. The results live here instead:
// a revisit renders instantly from this store, and a fetch happens only when
// the slot is empty (first visit), the user asks for a refresh, or a new
// portfolio is saved (invalidate()).
import type { PortfolioRiskReport, RebalanceCompare, TaxSignalsReport } from '$api/client';

class DashData {
	risk = $state<PortfolioRiskReport | null>(null);
	tax = $state<TaxSignalsReport | null>(null);
	compare = $state<RebalanceCompare | null>(null);

	/** A new portfolio makes every cached payload wrong. Called on save. */
	invalidate() {
		this.risk = null;
		this.tax = null;
		this.compare = null;
	}
}

export const dashData = new DashData();
