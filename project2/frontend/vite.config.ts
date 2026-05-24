import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
const allowedHosts = process.env.ALLOWED_HOSTS
  ? process.env.ALLOWED_HOSTS.split(',')
  : ['.up.railway.app', 'localhost'];

export default defineConfig({
  plugins: [react()],
  preview: {
    allowedHosts,
  },
})
