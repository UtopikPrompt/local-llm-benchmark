"""HTTP layer for the API.

FastAPI handles the HTTP concerns (routing, request parsing, JSON responses)
natively. This module is a thin delegator: :func:`create_app` builds the
application by wrapping the :class:`local_llm_benchmark.server.api.controller.Controller`,
which owns the routing, the static dashboard mount and the error translation.
The controller is the sole HTTP bridge to the HTTP-agnostic service layer
(:mod:`local_llm_benchmark.server.api.services`).
"""

from __future__ import annotations

from fastapi import FastAPI

from local_llm_benchmark.server.api import controller as controller_layer


def create_app(config_path: str | None = None) -> FastAPI:
    """Build the FastAPI application.

    *config_path* points at a configuration file whose engines are loaded into
    ``Defaults.engines`` so the dashboard's engine dropdown and the ``/run``
    multi-engine selection use them. Defaults to the project-root ``config.yaml``
    when present. Delegates entirely to the HTTP controller.
    """
    return controller_layer.create_app(config_path)


