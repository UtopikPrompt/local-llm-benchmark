// vite.config.ts
import { sveltekit } from "file:///workspaces/local-llm-benchmark/node_modules/.pnpm/@sveltejs+kit@2.70.3_@sveltejs+vite-plugin-svelte@3.1.2_svelte@4.2.20_vite@5.4.21_@type_4dc09b842f0e993aaabcf9328d912025/node_modules/@sveltejs/kit/src/exports/vite/index.js";
import { defineConfig } from "file:///workspaces/local-llm-benchmark/node_modules/.pnpm/vite@5.4.21_@types+node@20.19.43/node_modules/vite/dist/node/index.js";
var vite_config_default = defineConfig({
  plugins: [sveltekit()],
  test: {
    include: ["src/**/*.{test,spec}.{js,ts}"],
    environment: "node",
    globals: true,
    setupFiles: ["src/test/setup.ts"]
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvd29ya3NwYWNlcy9sb2NhbC1sbG0tYmVuY2htYXJrXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCIvd29ya3NwYWNlcy9sb2NhbC1sbG0tYmVuY2htYXJrL3ZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy93b3Jrc3BhY2VzL2xvY2FsLWxsbS1iZW5jaG1hcmsvdml0ZS5jb25maWcudHNcIjtpbXBvcnQgeyBzdmVsdGVraXQgfSBmcm9tICdAc3ZlbHRlanMva2l0L3ZpdGUnO1xuaW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSc7XG5cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIHBsdWdpbnM6IFtzdmVsdGVraXQoKV0sXG4gIHRlc3Q6IHtcbiAgICBpbmNsdWRlOiBbJ3NyYy8qKi8qLnt0ZXN0LHNwZWN9Lntqcyx0c30nXSxcbiAgICBlbnZpcm9ubWVudDogJ25vZGUnLFxuICAgIGdsb2JhbHM6IHRydWUsXG4gICAgc2V0dXBGaWxlczogWydzcmMvdGVzdC9zZXR1cC50cyddLFxuICB9LFxufSk7XG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQStRLFNBQVMsaUJBQWlCO0FBQ3pTLFNBQVMsb0JBQW9CO0FBRTdCLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxVQUFVLENBQUM7QUFBQSxFQUNyQixNQUFNO0FBQUEsSUFDSixTQUFTLENBQUMsOEJBQThCO0FBQUEsSUFDeEMsYUFBYTtBQUFBLElBQ2IsU0FBUztBQUFBLElBQ1QsWUFBWSxDQUFDLG1CQUFtQjtBQUFBLEVBQ2xDO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
