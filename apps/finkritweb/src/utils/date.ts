/** Today as an ISO YYYY-MM-DD string (local time). */
export function todayISO(): string {
	const d = new Date();
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * Coerce a missing / epoch-ish acquired date to today. The parser (or a stray
 * CSV) can hand back nothing or 1970-01-01; a holding you own was not acquired
 * in 1970, so default to today rather than showing a nonsense date.
 */
export function acquiredOrToday(value: string | null | undefined): string {
	if (!value || value <= '1970-01-02') return todayISO();
	return value;
}
