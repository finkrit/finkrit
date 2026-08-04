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

/** One specialist's own reply, before the orchestrator folded it into the
 *  combined answer. Read off the agent run rather than off the final text, so
 *  it is what the specialist actually said and can be checked against. */
export interface SpecialistAnswer {
	name: string; // risk, performance, optimization, tax
	question: string; // the sub-question the orchestrator handed it
	answer: string;
}

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

/** One lot worth harvesting today. Lot level on purpose: this comes off the
 *  deterministic endpoint (code, not the model), and "which lot" is what makes
 *  the signal actionable. */
export interface HarvestSignal {
	ticker: string;
	lot_id: string;
	quantity: number;
	acquired: string; // ISO date
	cost_basis: number;
	market_value: number;
	unrealized_loss: number; // positive magnitude
	is_long_term: boolean;
	estimated_saving: number;
}

/** One short-term lot near the 365-day boundary. `action` is decided server
 *  side ("hold" for a gain lot, "harvest_now" for a loss lot) so every surface
 *  words the advice identically. */
export interface CountdownSignal {
	ticker: string;
	lot_id: string;
	quantity: number;
	acquired: string; // ISO date
	market_value: number;
	unrealized_gain: number; // signed
	transition_date: string; // ISO date
	days_until: number;
	action: 'hold' | 'harvest_now';
	estimated_saving: number;
}

export interface TaxSignalsReport {
	as_of: string;
	short_term_rate: number;
	long_term_rate: number;
	total_harvestable_loss: number;
	estimated_harvest_saving: number;
	harvest: HarvestSignal[];
	wash_sale_blocked: string[];
	countdowns: CountdownSignal[];
}

export interface RebalanceSell {
	ticker: string;
	sell_value: number;
	executed_value: number;
	realized_gain: number;
	short_term_gain: number;
	long_term_gain: number;
	is_harvest: boolean;
	is_partial: boolean;
	lots_touched: number;
}

export interface RebalancePlan {
	sells: RebalanceSell[];
	deferred: string[];
	realized_gain: number;
	short_term_gain: number;
	long_term_gain: number;
	harvested_loss: number;
	residual_drift: number; // fraction of portfolio value
}

/** The fixed three-strategy menu, every row computed off the same target
 *  weights and budget so the rows are actually comparable. */
export interface RebalanceCompare {
	as_of: string;
	objective: string;
	method: string;
	tolerance: number;
	gain_budget: number | null;
	target_weights: Record<string, number>;
	strategies: Record<'full' | 'band_edge' | 'partial_fill', RebalancePlan>;
	note: string;
}

/** One thing the agent did, reported while it was happening. `kind` is
 *  'specialist' for an orchestrator delegation (the grain the pills show) and
 *  'tool' for a specialist's own domain call. `call_id` pairs a finish back to
 *  its start, which position cannot do: a fan out runs its specialists
 *  concurrently, so they finish in whatever order they finish. */
export interface ChatStep {
	kind: 'specialist' | 'tool';
	status: 'started' | 'finished' | 'retry';
	name: string;
	detail: string; // the sub-question handed to a specialist
	call_id: string;
	args: Record<string, unknown>; // a tool's parameters
	content: string; // what came back
}

export interface AskAnswer {
	answer: string;
	conversation_id: string;
	specialists: string[];
	specialist_answers: SpecialistAnswer[];
}

/** One frame of the prefetch stream: the opening ticker list, then a line per
 *  ticker as its download completes, then the end marker. */
export type PrefetchEvent =
	| { event: 'start'; tickers: string[] }
	| { ticker: string; status: 'ready' | 'error'; detail?: string }
	| { event: 'end' };

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

/** Read a server sent event stream, calling `onFrame` with each parsed frame.
 *
 *  Hand rolled rather than EventSource for two reasons: EventSource treats the
 *  end of a finite stream as a dropped connection and reconnects forever, and
 *  it cannot issue a POST, which the ask stream needs in order to carry the
 *  question. Resolves when the server closes the stream. */
async function readEventStream<T>(res: Response, onFrame: (frame: T) => void): Promise<void> {
	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: res.statusText }));
		throw new ApiError(res.status, body.detail ?? res.statusText);
	}
	if (!res.body) return;
	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		// Frames are separated by a blank line. Whatever follows the last
		// separator is an incomplete frame, kept for the next chunk.
		const frames = buffer.split('\n\n');
		buffer = frames.pop() ?? '';
		for (const frame of frames) {
			const data = frame
				.split('\n')
				.filter((line) => line.startsWith('data: '))
				.map((line) => line.slice(6))
				.join('');
			if (data) onFrame(JSON.parse(data) as T);
		}
	}
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

	// Warm the server's data caches, reporting each ticker as its download lands.
	prefetch: async (portfolioId: string, onEvent: (e: PrefetchEvent) => void): Promise<void> =>
		readEventStream(await fetch(`/api/portfolio/${portfolioId}/prefetch`), onEvent),

	// Ask, and watch the work happen. Each step reports a specialist starting
	// or finishing (or a tool it called), so a multi specialist run shows its
	// fan out instead of sitting silent.
	//
	// A failure arrives as a frame, not a status code: by the time the run
	// raises, the response has already begun and the status line is spent. So
	// this rejects on a stream that ends in an error frame, and on one that
	// ends with no answer at all (a dropped connection mid-run).
	askStream: async (
		question: string,
		conversationId: string | undefined,
		onStep: (step: ChatStep) => void
	): Promise<AskAnswer> => {
		const res = await fetch('/api/ask/stream', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question, conversation_id: conversationId ?? null })
		});

		let answer: AskAnswer | undefined;
		let failure: string | undefined;
		await readEventStream<Record<string, unknown>>(res, (frame) => {
			if (frame.type === 'step') onStep(frame as unknown as ChatStep);
			else if (frame.type === 'answer') answer = frame as unknown as AskAnswer;
			else if (frame.type === 'error') failure = String(frame.detail);
		});

		if (failure) throw new ApiError(500, failure);
		if (!answer) throw new ApiError(500, 'The answer stream ended before an answer arrived.');
		return answer;
	},

	// Deterministic tax view: harvest candidates, wash sale warnings, long term
	// countdowns. No LLM behind this, so it is safe to refetch on every visit.
	taxSignals: (portfolioId: string) =>
		fetch(`/api/portfolio/${portfolioId}/tax/signals`).then((r) => asJson<TaxSignalsReport>(r)),

	// The fixed strategy menu (full / band_edge / partial_fill) over one shared
	// target. gain_budget undefined means unlimited (no budget row constraint).
	rebalanceCompare: (
		portfolioId: string,
		opts: { objective?: string; gainBudget?: number; tolerance?: number } = {}
	) => {
		const params = new URLSearchParams();
		if (opts.objective) params.set('objective', opts.objective);
		if (opts.gainBudget !== undefined) params.set('gain_budget', String(opts.gainBudget));
		if (opts.tolerance !== undefined) params.set('tolerance', String(opts.tolerance));
		const qs = params.toString();
		return fetch(`/api/portfolio/${portfolioId}/rebalance/compare${qs ? `?${qs}` : ''}`).then(
			(r) => asJson<RebalanceCompare>(r)
		);
	},

	// Pass the conversationId returned by the previous turn to keep the thread,
	// which is what makes a follow-up like "and how does that compare?" work.
	// Omit it to start fresh, the server then issues a new id.
	ask: (question: string, conversationId?: string) =>
		fetch('/api/ask', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question, conversation_id: conversationId ?? null })
		}).then((r) =>
			asJson<{
				answer: string;
				conversation_id: string;
				specialists: string[];
				specialist_answers: SpecialistAnswer[];
			}>(r)
		),

	resetConversation: (conversationId: string) =>
		fetch(`/api/ask/${conversationId}/reset`, { method: 'POST' })
};
