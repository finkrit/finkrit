import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
export default {
	compilerOptions: {
		// Runes everywhere except node_modules (libs may not be rune-mode).
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	kit: {
		// Static SPA: `npm run build` output lands straight in services/api's
		// static dir; FastAPI serves it. fallback -> client-side routing works
		// on deep links.
		adapter: adapter({
			pages: '../../services/api/finkritserver/static',
			assets: '../../services/api/finkritserver/static',
			fallback: 'index.html'
		}),
		// Structure mirrors the wider app layout: feature-grouped modules under
		// src/, imported by short aliases instead of long relative paths.
		alias: {
			$components: 'src/components',
			$stores: 'src/stores',
			$api: 'src/api',
			$theme: 'src/theme',
			$utils: 'src/utils'
		}
	}
};
