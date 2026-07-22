// Presentation formatters shared across the portfolio views. Pure and
// framework free, so they unit test in isolation and reuse anywhere a number
// needs to reach the screen. Keep display formatting out of components and
// out of the pure metrics layer, both call through here.

// undefined lets Intl pick the runtime locale rather than pinning one.
const LOCALE = undefined;

export function money(value: number, currency = 'USD'): string {
	try {
		return new Intl.NumberFormat(LOCALE, {
			style: 'currency',
			currency,
			maximumFractionDigits: 2
		}).format(value);
	} catch {
		// An unknown currency code makes Intl throw. Fall back to a plain amount.
		return `${value.toFixed(2)} ${currency}`;
	}
}

export function compactMoney(value: number, currency = 'USD'): string {
	try {
		return new Intl.NumberFormat(LOCALE, {
			style: 'currency',
			currency,
			notation: 'compact',
			maximumFractionDigits: 1
		}).format(value);
	} catch {
		return money(value, currency);
	}
}

export function percent(fraction: number, digits = 1): string {
	return `${(fraction * 100).toFixed(digits)}%`;
}

export function shares(quantity: number): string {
	// Whole shares read cleaner without a trailing .00. Fractional shares keep
	// up to four places, which covers the fractional lots brokers report.
	return Number.isInteger(quantity)
		? quantity.toString()
		: quantity.toLocaleString(LOCALE, { maximumFractionDigits: 4 });
}
