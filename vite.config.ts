import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

const OLLAMA_TARGET = "http://localhost:11434";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      // Forward the engine's `/v1/*` requests through the Vite dev origin
      // (5173) so browser-side `fetch` requests are not blocked by CORS.
      // Ollama does not send `Access-Control-Allow-Origin` headers, so the
      // proxy rewrites them here instead. `configureResponse` is a runtime
      // proxy option not present in Vite's public types, hence the cast.
      "/v1": {
        target: OLLAMA_TARGET,
        changeOrigin: true,
        // Ollama's API already uses the `/v1/` prefix (e.g. `/v1/models`),
        // so the path must be forwarded unchanged.
        rewrite: (path: string) => path,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        configureResponse: (res: any) => {
          res.headers.set("access-control-allow-origin", "*");
          return res;
        },
      } as any,
    },
  },
  test: {
    include: ["src/**/*.{test,spec}.{js,ts}"],
    environment: "node",
    globals: true,
    setupFiles: ["src/test/setup.ts"],
  },
});
