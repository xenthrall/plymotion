import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately (`plymotion --dev`, port 8765) and
// Vite proxies /api and /auth to it, so the session cookie lands on the
// Vite origin. The production build is written into the Python package and
// served by FastAPI itself.
const API = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: API, changeOrigin: true },
      "/auth": { target: API, changeOrigin: true },
    },
  },
  build: {
    outDir: "../src/plymotion/web",
    emptyOutDir: true,
    chunkSizeWarningLimit: 900,
  },
});
