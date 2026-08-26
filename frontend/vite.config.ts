import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The backend runs on port 8000. In dev, /api requests are proxied there so the
// browser talks to the same origin (no CORS). For a production build, set
// VITE_API_BASE to an absolute backend URL, or serve behind a reverse proxy.
const backend = process.env.VITE_API_BASE || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
      },
      '/docs': {
        target: backend,
        changeOrigin: true,
      },
      '/redoc': {
        target: backend,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: backend,
        changeOrigin: true,
      },
    },
  },
});
