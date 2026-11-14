import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so the static build runs from any folder or GitHub Pages path
export default defineConfig({
  plugins: [react()],
  base: "./",
  // no SPA fallback: a missing glyph range must be a 404, not index.html
  appType: "mpa",
  build: { chunkSizeWarningLimit: 1500 },
});
