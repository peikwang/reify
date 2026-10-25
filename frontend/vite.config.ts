import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const backend = process.env.REIFY_BACKEND || "http://127.0.0.1:7801";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/p": backend,
      "/s": backend,
      "/media": backend,
      "/apps": backend,
    },
  },
  build: {
    outDir: "../web/dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
