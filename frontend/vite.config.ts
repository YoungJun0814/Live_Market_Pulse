import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("react-leaflet") || id.includes("leaflet")) {
            return "map-vendor";
          }
          if (id.includes("recharts")) {
            return "chart-vendor";
          }
          if (id.includes("framer-motion")) {
            return "motion-vendor";
          }
          if (id.includes("socket.io-client")) {
            return "socket-vendor";
          }
        },
      },
    },
  },
});
