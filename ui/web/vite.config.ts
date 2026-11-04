/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Where `npm run dev` finds the Python server. Set POKER_SERVER_PORT if you started that with
// `python ui/play.py --port`.
const pythonServer = `http://127.0.0.1:${process.env.POKER_SERVER_PORT || 8000}`

export default defineConfig({
  plugins: [react()],
  server: {
    // Only this computer can connect, the same as the Python server.
    host: '127.0.0.1',
    // The web app calls the same addresses here as when the Python server serves it.
    proxy: {
      '/api': pythonServer,
      '/ws': { target: pythonServer, ws: true },
    },
  },
  test: {
    // Components render into a simulated browser page.
    environment: 'jsdom',
  },
})
