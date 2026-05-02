import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Inside Docker, set VITE_API_PROXY_TARGET=http://server:8000 so the dev
// proxy reaches the FastAPI service over the compose network. Falls back
// to localhost for native `npm run dev`.
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
        ws: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
