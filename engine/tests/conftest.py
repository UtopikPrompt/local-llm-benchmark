"""Shared pytest fixtures and constants for the engine test suite."""

from __future__ import annotations

from typing import Any

# Default engine input used across the test suite.
DEFAULT_ENGINE_INPUT: dict[str, Any] = {
    "query": "What is the capital of France?",
    "model": "qwen2.5:7b",
    "temperature": 0.7,
    "max_tokens": 256,
}