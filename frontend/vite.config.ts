import { defineConfig } from 'vite'
import path from 'node:path'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // recharts is a single monolithic module (~560 kB min) used only on
    // chart-heavy routes, which are code-split into on-demand chunks via
    // lazy() in the router. Raising the warning limit keeps the build honest
    // — the initial bundle stays well under 500 kB (see chunk listing).
    chunkSizeWarningLimit: 650,
    rollupOptions: {
      output: {
        manualChunks: {
          // Heavy charting lib — only used on actuals/portfolio/dashboard
          // routes, so it loads on demand instead of blocking first paint.
          charts: ['recharts'],
          // Blueprint canvas — only used on /blueprints/:id/canvas.
          'blueprint-canvas': ['@xyflow/react'],
          // Markdown rendering — reports and marketplace detail pages.
          markdown: ['react-markdown'],
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/reports': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
