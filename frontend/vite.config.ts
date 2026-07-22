import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat':   'http://127.0.0.1:8080',
      '/rag':    'http://127.0.0.1:8080',
      '/agent':  'http://127.0.0.1:8080',
      '/ingest': 'http://127.0.0.1:8080',
      '/eval':   'http://127.0.0.1:8080',
      '/history': 'http://127.0.0.1:8080',
    },
  },
  build: {
    outDir: '../app/static',
    emptyOutDir: true,
  },
})
