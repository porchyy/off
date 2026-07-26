// Vite config — proxy /api to the FastAPI backend during dev so the existing
// relative-path fetch calls in app.js keep working unchanged.

import { defineConfig } from 'vite';

const backendTarget = process.env.POSTUREAI_BACKEND_URL || 'http://localhost:8000';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'esnext',
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
});
