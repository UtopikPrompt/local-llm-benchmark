import { defineConfig } from "astro/config";
import node from "@astrojs/node";

/** @type {import('astro').Config} */
const config = defineConfig({
  // This project is CommonJS-only: package.json does NOT set "type": "module".
  // Astro config must therefore be a .mjs file with CommonJS syntax.
  output: "server",
  // Serve the Parquet files written by benchmark runs directly from disk.
  // "always" makes /runtime/ and /runtime/run/{id} resolve to their pages.
  trailingSlash: "always",
  adapter: node({
    mode: "standalone",
    jsc: {
      target: "node20",
    },
  }),
  // Default: use the Rust compiler (@astrojs/compiler-rs). It parses Astro
  // block markup ({#each}/{#if}) AND frontmatter object-literals like
  // `redirect({...})`, which the JS/esbuild fallback parser cannot.
  experimental: {
    rustCompiler: true,
  },
  vite: {
    // Keep the Python cache directory (default: ./cache) out of the build.
    server: {
      port: 4321,
    },
  },
});

export default config;
local-llm-benchmark
