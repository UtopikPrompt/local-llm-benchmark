# Module — UI runtime, cache, APIs

## Two UI paths, one code base

- **Interactive** (Astro server actions): local, in-browser workflow.
- **Remote / headless** (REST API route): drives the same benchmark over the network.

Both paths delegate to the CLI and share the same result cache.

## Version tags (staleness)

Key caches by stable **version tags** so results do not go stale:
- **Engine/model + benchmark/seed**
- **Judge model/seed**

## Cache

- **One cache shared** across the API and UI (ADR-010, ADR-014).
- **Gitignored** local result cache.
- **LRU eviction** by max size, plus **age-aware** eviction.
- Cache identity uses the version tags above (ADR-018).

## Guardrails

- Never implement benchmark logic in the UI; only wrap CLI output.
- Keep the cache shared and version-keyed. Do not bypass LRU/age eviction.
- Do not store model-specific logic in the UI layer.
