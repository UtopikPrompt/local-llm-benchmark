# ADR 0001: ES-module architecture for the web dashboard

- **Status:** accepted
- **Date:** 2026-09-13
- **Deciders:** local-llm-benchmark team

## Context and problem

The web dashboard (`web/`) was a single, ~600-line `main.js` IIFE containing all
UI state and every feature (dashboard, benchmark, challenges). As the dashboard
grew, this "big ball of mud" file became hard to read, test, and maintain:

- All mutable UI state (selected models, active engine, tasks, filters) lived in
  one closure, so every feature module had to guess at shared state.
- Cross-feature data flows (e.g. selected models in `models.js` feeding the
  results table in `results.js`) were implicit and fragile.
- There were no per-feature units of code to review or update in isolation.

## Decision

Author the dashboard as a set of small **ES module feature files** under
`web/ui/*.js`, each exporting a narrow surface of functions, and share **one**
`state` object (defined and exported by `state.js`) as the single source of
truth. Bundle the modules with **esbuild** into a single IIFE (`web/ui/main.js`)
so the server continues to serve one self-contained script.

### Rationale

- **One shared `state` object.** Every module imports the default export from
  `state.js`, so state is explicit, observable, and free of closure coupling.
- **Thin module surface.** Each module exports only the functions it needs
  (`state.js` exports `state` only; `dom.js` exports the default `dom` only),
  which keeps the dependency graph readable and the bundles small.
- **Single entry + single output.** `app.js` is the only entry point and imports
  exactly the functions each view needs. esbuild bundles it into one IIFE, so no
  bundler config, build tooling, or module-serving changes are required in the
  server. The dashboard behaves identically to the old single-script file.

## Consequences

- **Build step.** The source modules are not directly servable; a build is
  required. `build_frontend.py` invokes esbuild
  (`python3 -m esbuild web/ui/app.js --bundle --format=iife --outfile=web/ui/main.js`)
  to produce the single IIFE. esbuild is a Python package, not a `node` binary,
  so it is declared as a `frontend` optional dependency in `pyproject.toml`.
- **`switchView` ownership.** View-scoped DOM containers (engine list, results,
  challenge list) are re-bound per tab in `views.js.switchView`, preventing
  cross-view contamination of module globals.
- **Testing.** The modules are thin and DOM-light, so they are hard to unit-test
  in isolation; the dashboard is validated end-to-end via Playwright against the
  running server. The `cls()` helper preserves a known boolean-logic NOTEBUG
  (out of scope for the follow-up).

## Status

Accepted. The modularization and esbuild bundling are complete, the build
succeeds (27340 bytes, byte-for-byte identical to the original bundle), and the
dashboard is verified working in a browser across all three tabs.
