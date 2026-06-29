import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat':   'http://localhost:8000',
      '/rag':    'http://localhost:8000',
      '/agent':  'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/eval':   'http://localhost:8000',
    },
  },
})
