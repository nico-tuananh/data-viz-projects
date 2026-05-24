import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  preview: {
    allowedHosts: ['.up.railway.app', 'frontend-data-viz-project-2-production.up.railway.app'],
  },
})
