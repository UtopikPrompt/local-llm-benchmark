---
name: UI stack standardization
type: decision
status: accepted
date: 2026-09-19
summary: Standardize the web UI on Astro, a buildless JavaScript framework.
---

# ADR-002: UI stack — Astro (buildless JavaScript framework)

## Context

ADR-001 deferred the UI-stack decision until the CLI was stable. The UI is a thin presentation
layer that delegates to the Python CLI. The chosen stack must:

- Be JavaScript-based (per the requirement).
- Be **buildless** — no mandatory build step — to preserve the project's "usable from a clone with
  minimal dependencies" constraint.
- Be the most popular framework in its class, so users are familiar with it and ecosystem support
  (plugins, components) is largest.

## Decision

Standardize the web UI on **Astro**. Astro is a JavaScript/TypeScript framework whose defining
feature is that it is *buildless* — it ships with no required build step (`astro dev` for
development and `astro check` for validation), and can ship an ad-hoc bundle with zero
configuration.

## Consequences

- **Zero build friction.** The UI runs with `astro dev` from the cloned repo, consistent with the
  CLI, and ships a static bundle without a separate build pipeline.
- **Minimal dependencies.** Astro has no required build toolchain, matching the project's
  dependency discipline.
- **Familiar, large ecosystem.** Astro is the most popular buildless JavaScript framework, so
  community components and integrations are abundant.
- **Isolated JS/TS toolchain.** The UI has its own Node/npm toolchain; it never needs to be
  installed for the CLI to work.
- **Islands architecture.** Use Astro's default Islands architecture (ADR-002, below).

## Alternatives Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Astro | Buildless, most popular JS framework | No build step, huge ecosystem, matches constraints | Requires JS/TS knowledge |
| B. SvelteKit | Popular Svelte framework | Fast dev, excellent DX | Not buildless by default (needs `vite build`) |
| C. SolidStart | SolidJS framework | Fast, reactive | Less mature ecosystem, not buildless |
| D. Next.js | Web-first React framework | Mature, huge ecosystem | Requires Node build, heavy deps, contradicts "from a clone" |
| E. Vite + plain SPA | Minimal, framework-agnostic | Very fast, minimal | No SSR, smaller ecosystem |

Option A (Astro) uniquely satisfies both "JavaScript" and "buildless" while being the most popular
such framework. Option B/S are not buildless by default; Option D adds a heavy build step against
the project's goals; Option E sacrifices the framework's ecosystem for marginal gains.

## Open points

- These open points have been resolved: Islands architecture (ADR-002, below) and interactive
  benchmark runs (ADR-006).
- Whether to standardize on Astro's built-in telemetry / dev-server caching once interactive runs
  are in production use.
