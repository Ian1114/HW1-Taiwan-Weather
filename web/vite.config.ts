import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const webDirectory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: webDirectory,
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, "/");
          if (normalizedId.includes("/recharts/") || normalizedId.includes("/d3-")) {
            return "chart-vendor";
          }
          if (normalizedId.includes("/leaflet/") || normalizedId.includes("/react-leaflet/")) {
            return "map-vendor";
          }
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(normalizedId)) {
            return "react-vendor";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
