/**
 * esbuild configuration for code splitting and chunk management
 * 
 * This configuration enables:
 * - Chunk-based bundling for code splitting
 * - Lazy loading via dynamic imports
 * - Optimized bundle structure
 */

import { defineConfig } from "esbuild";

export default defineConfig({
  bundle: true,
  
  // Output directory for bundled chunks
  outdir: "dist/static/js",
  outbase: "src",
  
  // Source maps for debugging
  sourcemap: true,
  
  // Minification settings
  minify: true,
  minifyWhitespace: true,
  minifySyntax: true,
  minifyIdentifiers: true,
  
  // Tree shaking for dead code elimination
  treeShaking: true,
  
  // Chunk configuration for code splitting
  chunks: {
    main: {
      // Main entry chunk - contains core application logic
      entryPoints: [
        "src/app/ui/app.js",
        "src/app/ui/models.js",
        "src/app/ui/state.js",
        "src/app/ui/dom.js",
        "src/app/ui/views.js",
        "src/app/ui/challenges.js",
        "src/app/ui/results.js",
        "src/app/ui/utils.js",
        "src/app/ui/web-vitals.js"
      ]
    },
    ui: {
      // UI components chunk - lazy loaded on demand
      entryPoints: [
        "src/app/ui/components/Header.js",
        "src/app/ui/components/Modal.js",
        "src/app/ui/components/Loading.js",
        "src/app/ui/components/ProgressBar.js",
        "src/app/ui/components/EngineCRUD.js",
        "src/app/ui/components/BenchmarkRunner.js"
      ]
    },
    api: {
      // API client chunk - lazy loaded for fetch operations
      entryPoints: [
        "src/app/ui/api/client.js",
        "src/app/ui/api/endpoints.js"
      ]
    },
    helpers: {
      // Utility helpers chunk - shared helpers
      entryPoints: [
        "src/app/ui/helpers/date.js",
        "src/app/ui/helpers/formatter.js",
        "src/app/ui/helpers/validators.js"
      ]
    }
  },
  
  // Platform and target
  platform: "browser",
  target: "es2020",
  
  // Additional optimizations
  maintainIndexes: true,
  keepNames: true,
  
  // Metadata for analysis
  metafile: true
});
