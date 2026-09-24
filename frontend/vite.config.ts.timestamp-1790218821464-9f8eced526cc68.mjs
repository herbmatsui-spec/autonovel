// vite.config.ts
import { defineConfig } from "file:///E:/hhh/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///E:/hhh/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
var backendUrl = process.env.VITE_BACKEND_URL || process.env.BACKEND_URL || "http://localhost:8200";
var vite_config_default = defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src"
    }
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
      "/system": { target: backendUrl, changeOrigin: true }
    }
  },
  preview: { host: true, port: 3e3 },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"]
        }
      }
    },
    chunkSizeWarningLimit: 1e3,
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
        statements: 50
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJFOlxcXFxoaGhcXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkU6XFxcXGhoaFxcXFxmcm9udGVuZFxcXFx2aXRlLmNvbmZpZy50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRTovaGhoL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVcIjtcclxuaW1wb3J0IHJlYWN0IGZyb20gXCJAdml0ZWpzL3BsdWdpbi1yZWFjdFwiO1xyXG5cclxuY29uc3QgYmFja2VuZFVybCA9IHByb2Nlc3MuZW52LlZJVEVfQkFDS0VORF9VUkwgfHwgcHJvY2Vzcy5lbnYuQkFDS0VORF9VUkwgfHwgXCJodHRwOi8vbG9jYWxob3N0OjgyMDBcIjtcclxuXHJcbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XHJcbiAgcGx1Z2luczogW3JlYWN0KCldLFxyXG4gIHJlc29sdmU6IHtcclxuICAgICBhbGlhczoge1xyXG4gICAgICAgJ0AnOiAnL3NyYycsXHJcbiAgICAgfSxcclxuICAgfSxcclxuICAgc2VydmVyOiB7XHJcbiAgICBob3N0OiB0cnVlLFxyXG4gICAgcG9ydDogNTE3MyxcclxuICAgIHByb3h5OiB7XHJcbiAgICAgIFwiL2FwaVwiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL2Vhc3lfbW9kZVwiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL2VkaXRvclwiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL2dyYXBoXCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvaGVhbHRoXCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvbWV0cmljc1wiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL2Jvb2tzXCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvcGxvdHNcIjogeyB0YXJnZXQ6IGJhY2tlbmRVcmwsIGNoYW5nZU9yaWdpbjogdHJ1ZSB9LFxyXG4gICAgICBcIi9lcGlzb2Rlc1wiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL3Rhc2tzXCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvc3R5bGVzXCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvbXVsdGltZWRpYVwiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL2NvbW1lcmNpYWxcIjogeyB0YXJnZXQ6IGJhY2tlbmRVcmwsIGNoYW5nZU9yaWdpbjogdHJ1ZSB9LFxyXG4gICAgICBcIi9jb3N0XCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvcGF0Y2hlc1wiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL25vdmVsXCI6IHsgdGFyZ2V0OiBiYWNrZW5kVXJsLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcclxuICAgICAgXCIvaWxsdXN0cmF0aW9uc1wiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL2V4cG9ydFwiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICAgIFwiL3N5c3RlbVwiOiB7IHRhcmdldDogYmFja2VuZFVybCwgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXHJcbiAgICB9LFxyXG4gIH0sXHJcbiAgcHJldmlldzogeyBob3N0OiB0cnVlLCBwb3J0OiAzMDAwIH0sXHJcbiAgYnVpbGQ6IHsgXHJcbiAgICBvdXREaXI6IFwiZGlzdFwiLFxyXG4gICAgcm9sbHVwT3B0aW9uczoge1xyXG4gICAgICBvdXRwdXQ6IHtcclxuICAgICAgICBtYW51YWxDaHVua3M6IHtcclxuICAgICAgICAgIHZlbmRvcjogW1wicmVhY3RcIiwgXCJyZWFjdC1kb21cIiwgXCJyZWFjdC1yb3V0ZXItZG9tXCJdXHJcbiAgICAgICAgfVxyXG4gICAgICB9XHJcbiAgICB9LFxyXG4gICAgY2h1bmtTaXplV2FybmluZ0xpbWl0OiAxMDAwLFxyXG4gICAgbWluaWZ5OiBcInRlcnNlclwiLFxyXG4gICAgdGVyc2VyT3B0aW9uczoge1xyXG4gICAgICBjb21wcmVzczoge1xyXG4gICAgICAgIGRyb3BfY29uc29sZTogdHJ1ZSxcclxuICAgICAgICBkcm9wX2RlYnVnZ2VyOiB0cnVlXHJcbiAgICAgIH1cclxuICAgIH1cclxuICB9LFxyXG4gIHRlc3Q6IHtcclxuICAgIGVudmlyb25tZW50OiBcImpzZG9tXCIsXHJcbiAgICBnbG9iYWxzOiB0cnVlLFxyXG4gICAgc2V0dXBGaWxlczogW1wiLi90ZXN0cy9zZXR1cC50c1wiXSxcclxuICAgIGNvdmVyYWdlOiB7XHJcbiAgICAgIHByb3ZpZGVyOiBcInY4XCIsXHJcbiAgICAgIHJlcG9ydGVyOiBbXCJ0ZXh0XCIsIFwianNvblwiLCBcImh0bWxcIl0sXHJcbiAgICAgIGV4Y2x1ZGU6IFtcInNyYy9tYWluLnRzeFwiLCBcInNyYy90eXBlcy8qKlwiXSxcclxuICAgICAgdGhyZXNob2xkczoge1xyXG4gICAgICAgIGxpbmVzOiA1MCxcclxuICAgICAgICBicmFuY2hlczogNTAsXHJcbiAgICAgICAgZnVuY3Rpb25zOiA1MCxcclxuICAgICAgICBzdGF0ZW1lbnRzOiA1MCxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgfSxcclxufSk7XHJcblxyXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQXFPLFNBQVMsb0JBQW9CO0FBQ2xRLE9BQU8sV0FBVztBQUVsQixJQUFNLGFBQWEsUUFBUSxJQUFJLG9CQUFvQixRQUFRLElBQUksZUFBZTtBQUU5RSxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUMsTUFBTSxDQUFDO0FBQUEsRUFDakIsU0FBUztBQUFBLElBQ04sT0FBTztBQUFBLE1BQ0wsS0FBSztBQUFBLElBQ1A7QUFBQSxFQUNGO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDUCxNQUFNO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ2pELGNBQWMsRUFBRSxRQUFRLFlBQVksY0FBYyxLQUFLO0FBQUEsTUFDdkQsV0FBVyxFQUFFLFFBQVEsWUFBWSxjQUFjLEtBQUs7QUFBQSxNQUNwRCxVQUFVLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ25ELFdBQVcsRUFBRSxRQUFRLFlBQVksY0FBYyxLQUFLO0FBQUEsTUFDcEQsWUFBWSxFQUFFLFFBQVEsWUFBWSxjQUFjLEtBQUs7QUFBQSxNQUNyRCxVQUFVLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ25ELFVBQVUsRUFBRSxRQUFRLFlBQVksY0FBYyxLQUFLO0FBQUEsTUFDbkQsYUFBYSxFQUFFLFFBQVEsWUFBWSxjQUFjLEtBQUs7QUFBQSxNQUN0RCxVQUFVLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ25ELFdBQVcsRUFBRSxRQUFRLFlBQVksY0FBYyxLQUFLO0FBQUEsTUFDcEQsZUFBZSxFQUFFLFFBQVEsWUFBWSxjQUFjLEtBQUs7QUFBQSxNQUN4RCxlQUFlLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ3hELFNBQVMsRUFBRSxRQUFRLFlBQVksY0FBYyxLQUFLO0FBQUEsTUFDbEQsWUFBWSxFQUFFLFFBQVEsWUFBWSxjQUFjLEtBQUs7QUFBQSxNQUNyRCxVQUFVLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ25ELGtCQUFrQixFQUFFLFFBQVEsWUFBWSxjQUFjLEtBQUs7QUFBQSxNQUMzRCxXQUFXLEVBQUUsUUFBUSxZQUFZLGNBQWMsS0FBSztBQUFBLE1BQ3BELFdBQVcsRUFBRSxRQUFRLFlBQVksY0FBYyxLQUFLO0FBQUEsSUFDdEQ7QUFBQSxFQUNGO0FBQUEsRUFDQSxTQUFTLEVBQUUsTUFBTSxNQUFNLE1BQU0sSUFBSztBQUFBLEVBQ2xDLE9BQU87QUFBQSxJQUNMLFFBQVE7QUFBQSxJQUNSLGVBQWU7QUFBQSxNQUNiLFFBQVE7QUFBQSxRQUNOLGNBQWM7QUFBQSxVQUNaLFFBQVEsQ0FBQyxTQUFTLGFBQWEsa0JBQWtCO0FBQUEsUUFDbkQ7QUFBQSxNQUNGO0FBQUEsSUFDRjtBQUFBLElBQ0EsdUJBQXVCO0FBQUEsSUFDdkIsUUFBUTtBQUFBLElBQ1IsZUFBZTtBQUFBLE1BQ2IsVUFBVTtBQUFBLFFBQ1IsY0FBYztBQUFBLFFBQ2QsZUFBZTtBQUFBLE1BQ2pCO0FBQUEsSUFDRjtBQUFBLEVBQ0Y7QUFBQSxFQUNBLE1BQU07QUFBQSxJQUNKLGFBQWE7QUFBQSxJQUNiLFNBQVM7QUFBQSxJQUNULFlBQVksQ0FBQyxrQkFBa0I7QUFBQSxJQUMvQixVQUFVO0FBQUEsTUFDUixVQUFVO0FBQUEsTUFDVixVQUFVLENBQUMsUUFBUSxRQUFRLE1BQU07QUFBQSxNQUNqQyxTQUFTLENBQUMsZ0JBQWdCLGNBQWM7QUFBQSxNQUN4QyxZQUFZO0FBQUEsUUFDVixPQUFPO0FBQUEsUUFDUCxVQUFVO0FBQUEsUUFDVixXQUFXO0FBQUEsUUFDWCxZQUFZO0FBQUEsTUFDZDtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
