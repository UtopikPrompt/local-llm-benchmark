"""The engine adapter seam (design §9, contract 1).

Every inference engine -- Ollama, LM Studio, and any future engine -- sits behind
this single, OpenAI-compatible interface. The orchestrator talks to
``EngineAdapter`` only, so adding an engine never touches the orchestration logic.

The contract mirrors the parts of the OpenAI ``/chat/completions`` response that
the benchmark needs. Engines may differ in how they express time-to-first-token,
token counts, or thinking time; the adapter normalises those engine-specific
shapes into the common :class:`CompletionResponse` fields below (design §7):

``ttft_ms``, ``input_tokens``, ``output_tokens``, ``response_latency_ms``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CompletionResponse:
    """Unified shape returned by every :meth:`EngineAdapter.completion`.

    The four numeric fields map 1:1 to the schema columns recorded for every
    run (design §7). ``throughput`` is derived there as
    ``output_tokens / (response_latency_ms / 1000)`` and should match.
    """

    text: str
    """The raw completion text (post any engine-specific formatting)."""

    ttft_ms: float
    """Time from request send to first token, in milliseconds."""

    input_tokens: int
    """Number of prompt tokens reported by the engine (0 if unknown)."""

    output_tokens: int
    """Number of completion tokens reported by the engine (0 if unknown)."""

    response_latency_ms: float
    """Total wall-clock latency of the completion, in milliseconds."""

    thinking_time_ms: float = 0.0
    """Optional thinking/processing time, in milliseconds (0 if unknown)."""

    def throughput_toks_s(self) -> float:
        """Tokens per second. ``0.0`` when no time elapsed or no tokens."""
        if self.response_latency_ms <= 0 or self.output_tokens <= 0:
            return 0.0
        return self.output_tokens / (self.response_latency_ms / 1000.0)


class AdapterError(RuntimeError):
    """Raised when an engine call cannot be completed.

    Wraps the underlying cause so the orchestrator sees a single error type
    regardless of which engine or library raised it.
    """


# The request payload is deliberately typed as ``dict`` (kept opaque) so that
# engine-specific differences are absorbed inside each adapter, exactly as the
# OpenAI-compatible contract intends. The payload is a subset of the OpenAI
# ``/chat/completions`` body: ``{"model", "prompt", "options"}``.
CompletionRequest = dict


class EngineAdapter:
    """Abstract base class for inference engine adapters.

    Subclasses point at a concrete engine (Ollama, LM Studio, ...) and implement
    :meth:`_do_completion`. They must also normalise that engine's response into
    the :class:`CompletionResponse` contract via :meth:`normalise_response`.

    The base class provides the single public entry point -- :meth:`completion`
    -- which times the call and raises :class:`AdapterError` on failure.
    """

    #: Short engine name, e.g. ``"ollama"``. Set by subclasses.
    engine_name: str = ""

    #: The OpenAI-compatible base URL for this engine (design §9, contract 1).
    base_url: str

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def completion(self, payload: CompletionRequest) -> CompletionResponse:
        """Send a completion request and return a normalised response.

        :param payload: OpenAI-compatible ``/chat/completions`` body, including
            at least ``model`` and ``prompt``. Engine-specific overrides live
            under the ``options`` key.
        :raises AdapterError: if the request fails or the response is invalid.
        """
        if not payload.get("model"):
            raise AdapterError("completion request is missing 'model'")
        if not payload.get("prompt"):
            raise AdapterError("completion request is missing 'prompt'")

        start = time.perf_counter()
        try:
            response = self._do_completion(payload)
        except AdapterError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrap
            raise AdapterError(
                f"{self.engine_name} engine call failed: {exc}"
            ) from exc
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Surface the measured total latency even when the engine itself reports
        # nothing -- it is the ground-truth wall-clock cost of the call.
        if response.response_latency_ms <= 0:
            response.response_latency_ms = elapsed_ms
        else:
            # Prefer the engine's measured value but never report less than the
            # wall clock, which would indicate a timing bug in the engine.
            response.response_latency_ms = max(
                response.response_latency_ms, elapsed_ms
            )
        return response

    def _do_completion(self, payload: CompletionRequest) -> CompletionResponse:
        """Engine-specific call. Raise :class:`AdapterError` on failure."""
        raise NotImplementedError

    def normalise_response(self, text: str, response: object) -> CompletionResponse:
        """Convert a raw engine response into a :class:`CompletionResponse`.

        :param text: the completion text extracted from ``response``.
        :param response: the engine-specific response object (or ``None``).
        """
        raise NotImplementedError
