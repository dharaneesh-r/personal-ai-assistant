import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat':   'http://127.0.0.1:8000',
      '/rag':    'http://127.0.0.1:8000',
      '/agent':  'http://127.0.0.1:8000',
      '/ingest': 'http://127.0.0.1:8000',
      '/eval':   'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../app/static',
    emptyOutDir: true,
  },
})
