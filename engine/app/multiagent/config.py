"""
AutoGen Configuration for Local LLM-Powered Multi-Agent Development

Supports:
- Ollama (http://localhost:11434/v1)
- LM Studio (http://localhost:1234/v1)
- OpenAI (fallback for manager/coordinator)

Each agent has its own model configuration, allowing task specialization.
"""

import os
from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class ModelConfig:
    """Configuration for a single model/agent"""
    model: str
    api_type: str
    api_base: str
    api_key: str
    timeout: int = 120
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    def to_llm_config(self) -> dict:
        """Convert to AutoGen llm_config format"""
        config = {
            "model": self.model,
            "api_type": self.api_type,
            "api_base": self.api_base,
            "api_key": self.api_key,
            "timeout": self.timeout,
            "temperature": self.temperature,
        }
        if self.max_tokens:
            config["max_tokens"] = self.max_tokens
        return config


def check_engine_health(api_base: str) -> bool:
    """Check if a local engine is running"""
    try:
        response = requests.get(f"{api_base.rstrip('/')}/models", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_available_models(api_base: str) -> list[str]:
    """Get list of available models from an engine"""
    try:
        response = requests.get(f"{api_base.rstrip('/')}/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "data" in data:  # OpenAI-compatible format
                return [m.get("id", m) for m in data["data"]]
            elif "models" in data:  # Ollama format
                return [m["name"] for m in data["models"]]
        return []
    except Exception as e:
        print(f"Warning: Could not fetch models from {api_base}: {e}")
        return []


class AgentConfig:
    """Manages agent configurations with fallback logic"""

    # Ollama local endpoint
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
    OLLAMA_AVAILABLE = check_engine_health(OLLAMA_API_BASE)

    # LM Studio local endpoint
    LM_STUDIO_API_BASE = os.getenv("LM_STUDIO_API_BASE", "http://localhost:1234/v1")
    LM_STUDIO_AVAILABLE = check_engine_health(LM_STUDIO_API_BASE)

    # OpenAI (fallback/manager)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_AVAILABLE = bool(OPENAI_API_KEY)

    @staticmethod
    def get_manager_config() -> ModelConfig:
        """
        Manager/Architect uses fastest available model.
        Prefers cloud (GPT-4) for quick, high-quality coordination,
        falls back to local Mistral.
        """
        if AgentConfig.OPENAI_AVAILABLE:
            return ModelConfig(
                model="gpt-4",
                api_type="open_ai",
                api_base="https://api.openai.com/v1",
                api_key=AgentConfig.OPENAI_API_KEY,
                temperature=0.7,
            )

        if AgentConfig.OLLAMA_AVAILABLE:
            models = get_available_models(AgentConfig.OLLAMA_API_BASE)
            model = next(
                (m for m in models if "mistral" in m.lower()),
                models[0] if models else "mistral",
            )
            return ModelConfig(
                model=f"ollama/{model}",
                api_type="open_ai",
                api_base=AgentConfig.OLLAMA_API_BASE,
                api_key="fake-key",
                temperature=0.7,
            )

        raise RuntimeError(
            "No local engines running. Start Ollama or LM Studio, or set OPENAI_API_KEY"
        )

    @staticmethod
    def get_backend_agent_config() -> ModelConfig:
        """
        Backend agent uses Ollama with coding-optimized model.
        Prefers Phi-3.5 or Mistral for code generation.
        """
        if not AgentConfig.OLLAMA_AVAILABLE:
            raise RuntimeError(
                f"Ollama not running at {AgentConfig.OLLAMA_API_BASE}. "
                "Start Ollama: ollama serve"
            )

        models = get_available_models(AgentConfig.OLLAMA_API_BASE)
        if not models:
            print(f"No models in Ollama. Pull one: ollama pull phi")
            raise RuntimeError("No models available in Ollama")

        # Prefer coding-optimized models
        preferred = [m for m in models if any(x in m.lower() for x in ["phi", "mistral", "neural-chat"])]
        model = preferred[0] if preferred else models[0]

        return ModelConfig(
            model=f"ollama/{model}",
            api_type="open_ai",
            api_base=AgentConfig.OLLAMA_API_BASE,
            api_key="fake-key",
            temperature=0.7,
        )

    @staticmethod
    def get_frontend_agent_config() -> ModelConfig:
        """
        Frontend agent uses LM Studio or Ollama with general-purpose model.
        Can be different from backend to benchmark different engines.
        """
        if AgentConfig.LM_STUDIO_AVAILABLE:
            models = get_available_models(AgentConfig.LM_STUDIO_API_BASE)
            model = models[0] if models else "neural-chat"
            return ModelConfig(
                model=model,
                api_type="open_ai",
                api_base=AgentConfig.LM_STUDIO_API_BASE,
                api_key="fake-key",
                temperature=0.7,
            )

        if AgentConfig.OLLAMA_AVAILABLE:
            models = get_available_models(AgentConfig.OLLAMA_API_BASE)
            model = next(
                (m for m in models if "neural-chat" in m.lower()),
                models[0] if models else "neural-chat",
            )
            return ModelConfig(
                model=f"ollama/{model}",
                api_type="open_ai",
                api_base=AgentConfig.OLLAMA_API_BASE,
                api_key="fake-key",
                temperature=0.7,
            )

        raise RuntimeError(
            "No local engines running. Start LM Studio or Ollama, or set OPENAI_API_KEY"
        )

    @staticmethod
    def get_reviewer_agent_config() -> ModelConfig:
        """
        Reviewer uses a different local model from backend to catch different issues.
        Provides fresh perspective on code quality.
        """
        if not AgentConfig.OLLAMA_AVAILABLE and not AgentConfig.LM_STUDIO_AVAILABLE:
            raise RuntimeError(
                "No local engines running. Start Ollama or LM Studio"
            )

        # Try to get a model from Ollama first
        if AgentConfig.OLLAMA_AVAILABLE:
            models = get_available_models(AgentConfig.OLLAMA_API_BASE)
            if len(models) >= 2:
                # Pick second model if available (different from backend)
                return ModelConfig(
                    model=f"ollama/{models[1]}",
                    api_type="open_ai",
                    api_base=AgentConfig.OLLAMA_API_BASE,
                    api_key="fake-key",
                    temperature=0.7,
                )
            elif models:
                return ModelConfig(
                    model=f"ollama/{models[0]}",
                    api_type="open_ai",
                    api_base=AgentConfig.OLLAMA_API_BASE,
                    api_key="fake-key",
                    temperature=0.7,
                )

        if AgentConfig.LM_STUDIO_AVAILABLE:
            models = get_available_models(AgentConfig.LM_STUDIO_API_BASE)
            if models:
                return ModelConfig(
                    model=models[0],
                    api_type="open_ai",
                    api_base=AgentConfig.LM_STUDIO_API_BASE,
                    api_key="fake-key",
                    temperature=0.7,
                )

        raise RuntimeError("Could not find any available models")

    @staticmethod
    def print_status():
        """Print availability status of local engines"""
        print("\n" + "=" * 60)
        print("LLM Engine Status")
        print("=" * 60)
        print(f"Ollama:     {'✓ Running' if AgentConfig.OLLAMA_AVAILABLE else '✗ Not running'}")
        if AgentConfig.OLLAMA_AVAILABLE:
            models = get_available_models(AgentConfig.OLLAMA_API_BASE)
            print(f"  Models: {', '.join(models[:3])}")
        print(f"LM Studio:  {'✓ Running' if AgentConfig.LM_STUDIO_AVAILABLE else '✗ Not running'}")
        if AgentConfig.LM_STUDIO_AVAILABLE:
            models = get_available_models(AgentConfig.LM_STUDIO_API_BASE)
            print(f"  Models: {', '.join(models[:3])}")
        print(f"OpenAI:     {'✓ Configured' if AgentConfig.OPENAI_AVAILABLE else '✗ Not configured'}")
        print("=" * 60 + "\n")
