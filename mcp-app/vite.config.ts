import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";
import path from "path";

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    target: "esnext",
  },
  server: {
    // Proxy API calls to Python server during development
    proxy: {
      "/api": "http://localhost:8765",
      "/health": "http://localhost:8765",
    },
  },
});
