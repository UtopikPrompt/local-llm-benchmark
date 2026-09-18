# Architectural Decision Record: Frontend Bundle Optimization

* **Title:** Frontend Bundle Optimization
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

Large JavaScript bundles shipped to the browser increase page load times, memory consumption, and time-to-interactive (TTI). In a benchmarking dashboard that users revisit frequently, these costs compound:

- **Load Time**: Monolithic bundles block first meaningful paint
- **Memory Usage**: Unused code is parsed and held in memory by the JS engine
- **Cache Inefficiency**: Any change to a large bundle invalidates the entire cached asset
- **Cold Start Penalty**: Every new session pays the full parse-and-compile cost

### Key Observations

1. The project bundles multiple UI modules (`app.js`, `challenges.js`, `dom.js`, `main.js`, `models.js`, `results.js`, `state.js`, `views.js`) via esbuild
2. Not all modules are needed on initial page load (e.g., detailed results views are only needed after a benchmark run)
3. The current `package.json` does not explicitly declare `sideEffects`, preventing tree-shaker from aggressively removing dead code
4. No chunk splitting is configured, meaning all code ships as one bundle

This decision formalizes three complementary strategies to address bundle bloat:

1. **Tree Shaking** — eliminate unused code at build time
2. **Code Splitting** — produce separate chunks for distinct feature areas
3. **Lazy Loading** — defer module parsing until a feature is actually used

---

## ✨ Decision

We will adopt a three-part frontend bundle optimization strategy backed by esbuild configuration.

### 1.1 Tree Shaking via `sideEffects` Declaration

Signal to the bundler that modules are free of side effects so unused exports can be removed at build time:

```json
// package.json
{
  "sideEffects": false
}
```

### 1.2 Code Splitting via esbuild Chunk Configuration

Split the bundle into named chunks aligned with application feature areas:

```javascript
// esbuild.config.js
import esbuild from 'esbuild';

export default function (ctx) {
  return {
    bundle: true,
    outdir: 'dist/static/js',
    outbase: 'src',
    sourcemap: true,
    minify: true,
    minifyWhitespace: true,
    minifySyntax: true,
    treeShaking: true,
    // Enable chunk splitting for large apps
    chunks: ['main', 'ui', 'api'],
  };
}
```

### 1.3 Lazy Loading via Dynamic Imports with Suspense

Defer non-critical view components until they are needed by the user:

```javascript
// UI components loaded on demand
import { lazy, Suspense } from 'vue';

const Dashboard = lazy(() => import('./components/Dashboard.vue'));
const ResultsTable = lazy(() => import('./components/ResultsTable.vue'));

// In component
<template>
  <Suspense>
    <template #default>
      <Dashboard />
    </template>
    <template #fallback>
      <div>Loading...</div>
    </template>
  </Suspense>
</template>
```

---

## 💡 Decision Rationale

| Factor | Rationale |
|--------|-----------|
| **Load Performance** | Tree shaking eliminates dead code; code splitting reduces initial payload |
| **Cache Efficiency** | Smaller, stable chunks are more likely to be browser-cached across deploys |
| **Developer Experience** | esbuild's native splitting support requires minimal configuration change |
| **User Experience** | Lazy loading defers non-critical modules, improving perceived responsiveness |

### Trade-offs Accepted

- **Build Complexity**: Chunk splitting requires coordinating chunk names and entry points
- **Network Requests**: Multiple smaller chunks increase the number of HTTP requests (mitigated by HTTP/2)
- **Fallback UI**: Lazy components require explicit `Suspense` boundaries and fallback states

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: No Optimization (Status Quo)

*Pros:* Zero implementation effort; single bundle is simple to reason about

*Cons:*
- All code downloaded and parsed on every page load
- Dead code inflates bundle size
- Poor cache efficiency — any change invalidates the whole bundle

*Rationale for Rejection:* The dashboard is expected to grow; deferring optimization increases future cost.

### Alternative B: Webpack with Module Federation

*Pros:*
- Mature ecosystem with broad plugin support
- Module Federation enables micro-frontend patterns

*Cons:*
- Significantly higher configuration complexity than esbuild
- Slower build times compared to esbuild's Go-based pipeline
- Introduces a new build tool dependency

*Rationale for Rejection:* The project already uses esbuild (see `esbuild.config.js`); switching build tools is disproportionate to the need.

### Alternative C: CDN-Hosted Third-Party Libraries

*Pros:*
- Frequently used libraries may already be cached in the browser
- Offloads bytes from the application bundle

*Cons:*
- Introduces a runtime dependency on an external CDN
- Privacy and integrity risks if CDN is compromised
- Adds latency if the CDN is cold

*Rationale for Rejection:* The application has no large third-party dependencies that justify CDN loading; tree shaking and splitting address the same goal internally.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* [**Reduced Initial Bundle Size**]: Tree shaking removes unused exports; in typical Vue/JS projects this reduces bundle size by 15–40%
* [**Faster Time-to-Interactive**]: Code splitting delivers only the code needed for the current view
* [**Improved Cache Hits**]: Stable chunks (e.g., core app logic) are not re-downloaded when unrelated view code changes
* [**Scalability**]: Each new feature module can be its own chunk without bloating the initial load

### 🔴 Negative Impacts / Trade-offs

* [**Lazy-load Flash**]: Users may see a brief loading fallback when navigating to a lazy-loaded view for the first time
* [**Chunk Coordination**]: Incorrect chunk boundaries can cause duplicate module inclusion across chunks
* [**Build Configuration Maintenance**]: Chunk names and entry points must be updated as the module structure evolves

---

## 🔗 Related ADRs

* [ADR 0002 - ESM Module Architecture](./0002-esm-module-architecture.md) — Establishes the module isolation principle that code splitting builds upon
* [ADR 0007 - Module Loading and Dependency Graph Management](./0007-module-discovery-pattern.md) — Dynamic module discovery complements lazy-loading patterns
