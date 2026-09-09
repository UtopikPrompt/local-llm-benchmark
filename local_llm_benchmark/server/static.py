"""Static asset serving for the dashboard.

The dashboard and its assets live at the project root next to this package at
``web``. This small helper knows how to mount them and stream saved reports
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse


class NotFound(Exception):
    """Raised when a requested path is missing or escapes the root."""


class Static:
    """Serve files from a directory rooted at *root*."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def resolve(self, request_path: str) -> Path | None:
        """Return the safe file for *request_path*, or ``None`` if forbidden."""
        try:
            target = (self._root / request_path.lstrip("/ ")).resolve()
        except (OSError, ValueError):
            return None
        # The target must be the root itself or live strictly inside it.
        if target != self._root and self._root not in target.parents:
            return None
        if not target.is_file():
            return None
        return target

    async def __call__(self, request: Any, **_params: Any) -> Any:
        target = self.resolve(request.url.path)
        if target is None:
            raise NotFound()
        suffix = target.suffix
        if suffix == ".json":
            return FileResponse(target, media_type="application/json")
        if suffix == ".html":
            return FileResponse(target, media_type="text/html")
        if suffix == ".js":
            return FileResponse(target, media_type="text/javascript")
        if suffix == ".css":
            return FileResponse(target, media_type="text/css")
        return FileResponse(target)


def install(app: FastAPI, root: Path) -> None:
    """Mount *root* as the static front door at ``/`` on *app*."""
    app.add_route("/", Static(root))
