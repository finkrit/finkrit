// Which middle-panel view is active. Left-sidebar items switch this; adding a
// view is: a new id here + a case in the middle panel + a sidebar item.
export type ViewId = 'portfolio' | 'risk';
export type Theme = 'light' | 'dark';

const THEME_KEY = 'finkrit:theme';

// SPA build (ssr disabled), so window/localStorage are always available here.
function initialTheme(): Theme {
	const stored = localStorage.getItem(THEME_KEY);
	if (stored === 'light' || stored === 'dark') return stored;
	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

class UIState {
	view = $state<ViewId>('portfolio');
	theme = $state<Theme>(initialTheme());

	select(view: ViewId) {
		this.view = view;
	}

	toggleTheme() {
		this.theme = this.theme === 'dark' ? 'light' : 'dark';
		localStorage.setItem(THEME_KEY, this.theme);
	}
}

export const ui = new UIState();
