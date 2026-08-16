import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/investors': 'http://localhost:8000',
      '/opportunities': 'http://localhost:8000',
      '/properties': 'http://localhost:8000',
      '/compare': 'http://localhost:8000',
      '/developers': 'http://localhost:8000',
    },
  },
})
