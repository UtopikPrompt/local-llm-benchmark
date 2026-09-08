# ADR 0002: Engine selection dropdown in the dashboard

- **Status:** Accepted
- **Date:** 2026-09-08
- **Deciders:** local-llm-benchmark authors

## Context

Once the config file supports a list of engines, the dashboard should let the
user pick one instead of hand-typing a `base-url` and `model`. Typing them by
hand is error-prone and bypasses the engines the user actually configured.

## Decision

Expose the configured engines through a new `GET /engines` endpoint and render
them as a `<select>` dropdown in the dashboard. Selecting an engine auto-fills
its `base-url` and `model` and sends the engine `name` back to `POST /run`,
which runs that engine from the multi-engine config.

## Consequences

- **No manual base URL / model typing:** the dropdown is the primary control;
  the base URL and model inputs are shown only while no engine is selected, so
  they auto-reappear when the user wants to type a base URL by hand.
- **`/run` accepts an engine name:** when the body includes an `engine` name, it
  selects the matching configured engine; otherwise it builds a fresh single
  engine from `base-url`/`model`.
- **Invalid selection is rejected:** selecting an engine name that is not
  configured returns HTTP 404.
- **Tests verify selection:** the engine tests patch `run_benchmark` and assert
  it was called with the chosen engine's config.
