import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["src/renderer/**/*.test.tsx"],
    setupFiles: ["src/renderer/testSetup.ts"],
    globals: true
  }
});
