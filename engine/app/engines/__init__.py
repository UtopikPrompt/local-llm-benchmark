"""Engine adapters for the local LLM benchmark backend.

Each adapter implements :class:`engine.app.engines.base.EngineAdapter`, the
unified OpenAI-compatible contract that lets the orchestrator drive every engine
through the same seam (design §9, contract 1). New engines are added by
implementing that interface -- never by editing the orchestrator.
"""

from __future__ import annotations

from app.engines.base import AdapterError, EngineAdapter

__all__ = ["EngineAdapter", "AdapterError"]
