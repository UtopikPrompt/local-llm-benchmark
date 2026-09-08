# ADR 0001: Source UI form defaults from the server

- **Status:** Accepted
- **Date:** 2025-09-08
- **Deciders:** local-llm-benchmark authors

## Context

The web dashboard (`ui/dashboard.html`) lets the user configure a benchmark run:
engine `base-url` and `model`, judge `base-url` and `model`, plus timeout,
concurrency, format, tasks, output path, and trials. Those values are also the
defaults used by the CLI and the config-file parser.

Previously the default values were scattered: the CLI's argparse defaults lived in
`runner.py`, the config-file parser duplicated them, and the dashboard's `<input>`
fields carried their own inline `value="..."` attributes. Changing a default meant
editing several places, and the dashboard's initial values drifted from the
canonical ones.

## Decision

Centralize the defaults in a single source of truth (`config.py` `Defaults`
class plus module-level `DEFAULT_*` constants) and have the dashboard load them
from the server on page load via a new `GET /defaults` endpoint.

- The server is the authority on defaults, not the HTML.
- The dashboard calls `/defaults` on load and writes each value into the
  corresponding form field, so a page reload restores the server's defaults
  instead of resetting to arbitrary previous state.

## Consequences

- **Single source of truth:** defaults are defined once in `config.py`; the CLI,
  config-file construction, and web dashboard all read from the same class.
- **Reload-safe form:** reloading the dashboard re-fetches `/defaults` and
  repopulates the fields, so the form never silently diverges from the configured
  defaults.
- **Graceful offline fallback:** if `/defaults` fails to load (e.g. the server is
  not running), `loadConfig()` is a no-op and the form keeps its placeholder text,
  remaining usable.
- **`/run` now derives** its fallback values from `Defaults` instead of hardcoded
  literals, so the API surface stays consistent with the source of truth.
