"""Application configuration for the local LLM benchmark backend.

Settings are resolved in this order: explicit value > environment variable >
hard-coded default. Keeping a plain ``Settings`` class (rather than
``pydantic_settings``) avoids adding a dependency that slice 0 does not need.
"""

from __future__ import annotations

from functools import lru_cache


class Settings:
    """Runtime configuration.

    Values are read from the environment at access time so that tests which set
    ``os.environ`` (e.g. ``TEST_DATABASE_PATH``) take effect without rebuilding
    the app.
    """

    def __init__(self) -> None:
        import os

        # --- Engine base URLs -------------------------------------------------
        self.ollama_base_url: str = os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.lm_studio_base_url: str = os.getenv(
            "LM_STUDIO_BASE_URL", "http://localhost:1234"
        )

        # --- Judge (LLM-as-judge) --------------------------------------------
        self.judge_base_url: str = os.getenv(
            "JUDGE_BASE_URL", self.lm_studio_base_url)
        self.judge_id: str = os.getenv("JUDGE_ID", "local-judge")

        # --- Default models ---------------------------------------------------
        self.default_models: dict[str, str] = {
            "phi-3.5-mini": "phi-3.5-mini",
            "llama-3.1-8b": "llama-3.1-8b-instruct",
        }

        # --- Persistence ------------------------------------------------------
        self.database_path: str = os.getenv(
            "TEST_DATABASE_PATH", ":memory:"
        )

    def as_dict(self) -> dict[str, object]:
        """Return a snapshot of the resolved settings (used by tests)."""
        return {
            "ollama_base_url": self.ollama_base_url,
            "lm_studio_base_url": self.lm_studio_base_url,
            "judge_base_url": self.judge_base_url,
            "judge_id": self.judge_id,
            "default_models": dict(self.default_models),
            "database_path": self.database_path,
        }


@lru_cache
def get_settings() -> Settings:
    """Return a cached process-wide :class:`Settings` instance."""
    return Settings()
