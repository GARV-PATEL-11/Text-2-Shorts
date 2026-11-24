// Faraday's frontend: React, built into dist/ and served by `text-2-shorts serve` (FastAPI) on one origin.
// `npm run dev` serves it with live reload on :5173 and sends API, media and preview requests to the backend on :8765.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    // Keep the browser's Host: the backend accepts writes only when Origin and Host match (same-origin check).
    proxy: Object.fromEntries(["/api", "/media", "/previews"].map((path) => [path, { target: backend, changeOrigin: false }])),
  },
  build: { outDir: "dist", emptyOutDir: true },
});
