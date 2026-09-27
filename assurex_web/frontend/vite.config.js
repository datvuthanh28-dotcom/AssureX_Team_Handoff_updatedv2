import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  root: '../..',
  base: command === 'build' ? '/AssureX_Team_Handoff/' : '/',
  publicDir: 'assurex_web/frontend/public',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'assurex_web/dist',
  },
  plugins: [react()],
}))
