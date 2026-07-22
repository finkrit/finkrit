// Thin fetch client for services/api. Relative paths ('/api/...') work
// unchanged in dev (Vite proxies to FastAPI, see vite.config.ts) and in the
// production build (FastAPI serves the SPA and the API same-origin).
//
// Types are hand-written to match the backend's pydantic/dataclass schemas
// (finkritserver/schemas.py, finagent/report/report.py, finagent/ingest.py).
// A generated client from /openapi.json would remove this duplication --
// worth doing once the API surface stabilizes; hand-written is fine for now.

export interface HoldingDraft {
	ticker: string;
	quantity: number;
	cost_per_share: number;
	acquired: string; // ISO date
	exchange?: string;
	currency?: string;
	// Per-row note from the parser when it had to guess or normalize a value.
	// Carried on the draft so the review table can surface it inline.
	confidence_note?: string | null;
}

export type ParsedHolding = HoldingDraft;

export interface ParsedPortfolio {
	name: string;
	holdings: ParsedHolding[];
	warnings: string[];
}

export interface PortfolioSummary {
	id: string;
	name: string;
}

export interface RiskParameters {
	as_of: string;
	lookback_start: string | null;
	lookback_end: string | null;
	interval: string;
	return_method: string;
	var_method: string;
	confidence: number;
	annualized: boolean;
	periods_per_year: number;
	benchmark_ticker: string | null;
}

export interface DrawdownSummary {
	max_drawdown: number;
	current_drawdown: number;
	periods: number;
	trough_date: string | null;
}

export interface PortfolioRiskReport {
	params: RiskParameters;
	volatility: number | null;
	variance: number | null;
	semivariance: number | null;
	downside_deviation: number | null;
	value_at_risk: number | null;
	conditional_value_at_risk: number | null;
	beta: number | null;
	max_drawdown: number | null;
	drawdown: DrawdownSummary | null;
	errors: Record<string, string>;
	portfolio_id: string;
	marginal_contributions: Record<string, number> | null;
	component_contributions: Record<string, number> | null;
}

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

async function asJson<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: res.statusText }));
		throw new ApiError(res.status, body.detail ?? res.statusText);
	}
	return res.json();
}

export const api = {
	health: () => fetch('/api/health').then((r) => asJson<{ status: string }>(r)),

	uploadCsv: (file: File) => {
		const form = new FormData();
		form.append('file', file);
		return fetch('/api/portfolio/upload', { method: 'POST', body: form }).then((r) =>
			asJson<ParsedPortfolio>(r)
		);
	},

	registerPortfolio: (name: string, holdings: HoldingDraft[]) =>
		fetch('/api/portfolio', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, holdings })
		}).then((r) => asJson<{ portfolio_id: string }>(r)),

	listPortfolios: () => fetch('/api/portfolios').then((r) => asJson<PortfolioSummary[]>(r)),

	report: (portfolioId: string, metrics: 'core' | 'all' = 'core') =>
		fetch(`/api/portfolio/${portfolioId}/report?metrics=${metrics}`).then((r) =>
			asJson<PortfolioRiskReport>(r)
		),

	ask: (question: string) =>
		fetch('/api/ask', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question })
		}).then((r) => asJson<{ answer: string }>(r))
};
