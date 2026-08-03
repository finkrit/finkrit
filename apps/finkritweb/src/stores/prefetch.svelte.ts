// Reactive state for one prefetch pass: which tickers the server is
// downloading and which have landed. Each data view owns an instance and
// renders DownloadProgress off it while its load() awaits run(). Kept as a
// class (not module state) because two views must not share a bar: switching
// views mid-download would show the old run's tickers under the new title.
import { api, type PrefetchEvent } from '$api/client';

export class PrefetchRun {
	tickers = $state<string[]>([]);
	status = $state<Record<string, 'ready' | 'error'>>({});

	readonly done = $derived(Object.keys(this.status).length);
	readonly total = $derived(this.tickers.length);

	/** Runs the server prefetch, resolving when every ticker has reported.
	 *  Rejects only on transport errors (e.g. 404 no portfolio); a single
	 *  ticker failing is reported in `status` and does not reject, matching
	 *  the endpoint's partial-success rule. */
	async run(portfolioId: string): Promise<void> {
		this.tickers = [];
		this.status = {};
		await api.prefetch(portfolioId, (e: PrefetchEvent) => {
			if ('event' in e) {
				if (e.event === 'start') this.tickers = e.tickers;
				return;
			}
			this.status = { ...this.status, [e.ticker]: e.status };
		});
	}
}
