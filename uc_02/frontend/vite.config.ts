import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Frontend talks to FastAPI only; the dev proxy avoids CORS since the
    // backend does not ship CORSMiddleware. Override with VITE_API_BASE_URL.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
