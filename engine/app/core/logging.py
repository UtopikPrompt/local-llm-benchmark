"""Structured, line-delimited JSON run logging.

Each log record is a dict that serializes to a single JSON line so downstream
tooling (and tests) can parse run events by ``event`` and ``run_id``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

LOGGER_NAME = "local_llm_benchmark"


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a configured logger.

    The root ``local_llm_benchmark`` logger is given a minimal stream handler
    with a JSON formatter. Child loggers inherit this configuration.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        extra = getattr(record, "data", None)
        if extra is not None:
            payload["data"] = extra
        return json.dumps(payload, default=str)


def log_run_event(
    logger: logging.Logger,
    event: str,
    **fields: Any,
) -> None:
    """Emit a structured run event as a JSON log line.

    ``event`` is the primary classifier (e.g. ``run_started``,
    ``completion_recorded``); ``**fields`` are merged into the record's ``data``
    object.
    """
    data = {"event": event, **fields}
    logger.info("run_event", extra={"data": data})
