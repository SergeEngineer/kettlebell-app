import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// In dev, Vite serves the SPA and forwards API/media calls to Flask (flask run --port 8088).
const flask = 'http://127.0.0.1:8088';

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,
    proxy: { '/api': flask, '/media': flask, '/static': flask, '/manifest.webmanifest': flask },
  },
  build: { outDir: 'dist', chunkSizeWarningLimit: 900 },
});
