import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendUrl = process.env.VITE_BACKEND_URL || process.env.BACKEND_URL || "http://localhost:8200";

export default defineConfig({
  plugins: [react()],
  resolve: {
     alias: {
       '@': '/src',
     },
   },
   server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: backendUrl, changeOrigin: true },
      "/easy_mode": { target: backendUrl, changeOrigin: true },
      "/editor": { target: backendUrl, changeOrigin: true },
      "/graph": { target: backendUrl, changeOrigin: true },
      "/health": { target: backendUrl, changeOrigin: true },
      "/metrics": { target: backendUrl, changeOrigin: true },
      "/books": { target: backendUrl, changeOrigin: true },
      "/plots": { target: backendUrl, changeOrigin: true },
      "/episodes": { target: backendUrl, changeOrigin: true },
      "/tasks": { target: backendUrl, changeOrigin: true },
      "/styles": { target: backendUrl, changeOrigin: true },
      "/multimedia": { target: backendUrl, changeOrigin: true },
      "/commercial": { target: backendUrl, changeOrigin: true },
      "/cost": { target: backendUrl, changeOrigin: true },
      "/patches": { target: backendUrl, changeOrigin: true },
      "/novel": { target: backendUrl, changeOrigin: true },
      "/illustrations": { target: backendUrl, changeOrigin: true },
      "/export": { target: backendUrl, changeOrigin: true },
      "/system": { target: backendUrl, changeOrigin: true },
    },
  },
  preview: { host: true, port: 3000 },
  build: { 
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"]
        }
      }
    },
    chunkSizeWarningLimit: 1000,
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["src/main.tsx", "src/types/**"],
      thresholds: {
        lines: 50,
        branches: 50,
        functions: 50,
        statements: 50,
      },
    },
  },
});

