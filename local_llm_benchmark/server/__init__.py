"""The web layer: HTTP front door for the benchmark.

The web package is the *front door* of the project. It exposes a small JSON
API (see :mod:`local_llm_benchmark.server.app`) and serves the dashboard. All
heavy lifting — engine selection, configuration, benchmarking — lives in the
shared core (:mod:`local_llm_benchmark`) and the API (:mod:`local_llm_benchmark.server.api`).
The web layer never talks to the core directly; it goes through the API so the
core stays pure and testable.
"""
