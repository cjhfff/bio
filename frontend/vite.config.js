import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',  // Enable remote access
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:8000',  // Use service name in Docker
        changeOrigin: true
      }
    }
  }
})
