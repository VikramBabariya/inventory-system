import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // needed inside Docker so Vite binds to 0.0.0.0, not just localhost
    proxy: {
      // Forwards /api/* → backend container on port 8000
      // Mirrors the Nginx proxy_pass rule used in production (nginx.conf)
      '/api': {
        target: 'http://backend:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
