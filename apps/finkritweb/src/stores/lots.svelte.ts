// Which positions are showing their tax lots.
//
// This lives in a store rather than in the table because the table is not the
// only thing that owns the answer. It remounts when the portfolio moves from
// review to saved, and the open rows should not silently snap shut underneath
// the user, and a fresh upload has to clear the old choices rather than carry
// them onto a different portfolio.
//
// Only explicit choices are stored. A position with no entry falls back to the
// caller's default, which is not constant: review opens multi lot positions so
// their inputs are reachable, while a saved portfolio starts collapsed. Storing
// the default instead of the choice would make "has the user touched this" and
// "is it open" the same question, and they are not.

class LotExpansion {
	#choices = $state<Record<string, boolean>>({});

	isOpen(key: string, fallback = false): boolean {
		return this.#choices[key] ?? fallback;
	}

	toggle(key: string, fallback = false) {
		this.#choices[key] = !this.isOpen(key, fallback);
	}

	allOpen(keys: string[], fallback = false): boolean {
		// An empty table is not "all open", otherwise a portfolio with nothing to
		// expand would offer to collapse it.
		return keys.length > 0 && keys.every((key) => this.isOpen(key, fallback));
	}

	/**
	 * Open or close every given position.
	 *
	 * `open` is a value, deliberately, not something recomputed per key. The
	 * caller's notion of "are they all open" is derived from this same state, so
	 * consulting it while writing would flip it partway through the loop and
	 * leave the table half toggled. Deciding once, outside, is the only correct
	 * order, and taking a plain boolean is what forces it.
	 */
	setAll(keys: string[], open: boolean) {
		for (const key of keys) this.#choices[key] = open;
	}

	clear() {
		this.#choices = {};
	}
}

export const lotExpansion = new LotExpansion();
