import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Kit config (adapter, aliases) now lives in svelte.config.js -- this file is
// just Vite plugins + the dev proxy.
export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// Dev only: forward /api/* to FastAPI so fetches use plain relative
		// paths ('/api/...') in dev and in the production build alike.
		proxy: {
			'/api': 'http://127.0.0.1:8000'
		}
	}
});
