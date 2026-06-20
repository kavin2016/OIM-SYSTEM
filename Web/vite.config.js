import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/departments': 'http://localhost:8000',
      '/roles': 'http://localhost:8000',
      '/positions': 'http://localhost:8000',
      '/domains': 'http://localhost:8000',
      '/permissions': 'http://localhost:8000',
      '/attendance': 'http://localhost:8000',
      '/ping': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  }
})
