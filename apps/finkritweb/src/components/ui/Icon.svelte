<script lang="ts">
	// Minimal inline-SVG icon set. Add a path to PATHS to add an icon; keeps us
	// off an icon-font dependency for the handful we need.
	type IconName =
		| 'chevron'
		| 'close'
		| 'send'
		| 'upload'
		| 'holdings'
		| 'risk'
		| 'chat'
		| 'lock'
		| 'sun'
		| 'moon';

	let { name, size = 18 }: { name: IconName; size?: number } = $props();

	const PATHS: Record<IconName, string> = {
		chevron: 'M6 9l6 6 6-6',
		close: 'M6 6l12 12M18 6L6 18',
		send: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z',
		upload: 'M12 16V4M6 10l6-6 6 6M4 20h16',
		holdings: 'M4 6h16M4 12h16M4 18h10',
		risk: 'M4 19V5M4 19h16M8 15l3-4 3 2 4-6',
		chat: 'M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z',
		lock: 'M6 10V7a6 6 0 0 1 12 0v3M5 10h14v11H5z',
		sun: 'M12 3v2M12 19v2M5 5l1.4 1.4M17.6 17.6L19 19M3 12h2M19 12h2M5 19l1.4-1.4M17.6 6.4L19 5M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
		moon: 'M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z'
	};
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.8"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	<path d={PATHS[name]} />
</svg>
