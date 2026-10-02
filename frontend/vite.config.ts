/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:7777";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      // In development the API lives in a different process; the browser never
      // notices because everything stays same-origin, cookies included.
      "/api": {
        target: BACKEND,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json-summary"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        // Type-only: no runtime code, so "0 %" here would be meaningless.
        "src/api/types.ts",
        // Ambient declaration emitted by Vite.
        "src/vite-env.d.ts",
        // Test infrastructure and the mounting entry point.
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/main.tsx",
      ],
      // The bar the suite must clear. Statements and lines are the meaningful
      // dimensions for this UI (98 %+). Function coverage is slightly lower and
      // the threshold reflects that deliberately: v8 counts every inline JSX
      // handler as a function, so "90 % functions" would mean clicking every
      // control in every state - churn without extra confidence.
      thresholds: {
        statements: 90,
        lines: 90,
        functions: 85,
        branches: 85,
      },
    },
  },
});
