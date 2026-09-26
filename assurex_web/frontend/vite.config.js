import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  root: '../..',
  base: '/AssureX_Team_Handoff/',
  publicDir: 'assurex_web/frontend/public',
  build: {
    outDir: 'assurex_web/dist',
  },
  plugins: [react()],
})
