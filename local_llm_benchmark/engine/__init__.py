"""Engine interface: the abstraction every engine implements.

Engines speak the OpenAI-compatible ``POST /v1/chat/completions`` interface
with seeded sampling (ADR-003). Each engine is an optional, additive plugin
never a hard dependency (ADR-003).

The :class:`Engine` base class defines the contract:
    * :meth:`Engine.chat`          -> single completion
    * :meth:`Engine.chat_stream`   -> streaming tokens for SSE (ADR-007)

Concrete engines (vLLM, llama.cpp, Ollama, HuggingFace Transformers) subclass
this and implement the HTTP transport. See docs/adr/ADR-003-Engine-interface.md.
"""

from local_llm_benchmark.engine.base import Engine, EngineConfig
from local_llm_benchmark.engine.registry import (
    available_engines,
    engine_names,
    get_engine_class,
)

__all__ = [
    "Engine",
    "EngineConfig",
    "available_engines",
    "engine_names",
    "get_engine_class",
]
