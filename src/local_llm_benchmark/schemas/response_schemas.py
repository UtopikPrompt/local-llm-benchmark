"""Response schemas for API endpoints.

These dataclasses define the response structures for all API endpoints,
providing type safety and validation for API responses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ModelInfo:
    """Information about a model."""
    id: str = field(metadata={"description": "Model identifier"})
    name: str = field(metadata={"description": "Model name"})
    config: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Model configuration"},
    )


@dataclass
class EngineInfo:
    """Information about an engine."""
    id: str = field(metadata={"description": "Engine identifier"})
    name: str = field(metadata={"description": "Engine name"})
    config: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Engine configuration"},
    )


@dataclass
class Usage:
    """Token usage statistics."""
    prompt_tokens: int = field(metadata={"description": "Tokens in prompt"})
    completion_tokens: int = field(metadata={"description": "Tokens in completion"})
    total_tokens: int = field(metadata={"description": "Total tokens used"})


@dataclass
class Choice:
    """A choice in a response."""
    index: int = field(metadata={"description": "Choice index"})
    message: Dict[str, Any] = field(
        metadata={"description": "Message content and role"}
    )
    finish_reason: Optional[str] = field(
        default=None,
        metadata={"description": "Reason for finishing generation"},
    )
    logprobs: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Log probabilities"},
    )


@dataclass
class LLMResponse:
    """LLM response structure.
    
    Represents the response from a language model, including the generated
    text and metadata.
    
    Attributes:
        id: Response identifier
        model: Model that generated the response
        choices: List of choices (typically one)
        usage: Token usage statistics
        system_fingerprint: Fingerprint for system prompt changes
        created: Timestamp of creation
    """
    id: Optional[str] = field(default=None)
    model: str = field(metadata={"description": "Model that generated the response"})
    choices: List[Choice] = field(
        default_factory=list,
        metadata={"description": "List of response choices"},
    )
    usage: Optional[Usage] = field(default=None)
    system_fingerprint: Optional[str] = field(default=None)
    created: Optional[datetime] = field(default=None)


@dataclass
class EngineResult:
    """Result of running an engine."""
    prompt: str = field(metadata={"description": "Original prompt"})
    response: Optional[str] = field(
        default=None,
        metadata={"description": "Generated response"},
    )
    success: bool = field(metadata={"description": "Whether generation succeeded"})
    metrics: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Performance metrics"},
    )
    error: Optional[str] = field(
        default=None,
        metadata={"description": "Error message if failed"},
    )


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    model: str = field(metadata={"description": "Model identifier"})
    engine_name: str = field(metadata={"description": "Engine name"})
    results: List[EngineResult] = field(
        default_factory=list,
        metadata={"description": "Individual prompt results"},
    )
    summary: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Benchmark summary statistics"},
    )
    errors: List[Dict[str, Any]] = field(
        default_factory=list,
        metadata={"description": "Errors encountered"},
    )


@dataclass
class EngineListResponse:
    """Response for listing engines."""
    engines: List[EngineInfo] = field(
        default_factory=list,
        metadata={"description": "List of engine information"},
    )
    total: int = field(
        default=0,
        metadata={"description": "Total number of engines"},
    )
    offset: int = field(
        default=0,
        metadata={"description": "Current offset"},
    )
    limit: int = field(
        default=20,
        metadata={"description": "Number of items per page"},
    )


@dataclass
class EngineDetailResponse:
    """Response for engine detail retrieval."""
    engine: EngineInfo = field(
        metadata={"description": "Engine information"}
    )


@dataclass
class ModelListResponse:
    """Response for listing models."""
    models: List[ModelInfo] = field(
        default_factory=list,
        metadata={"description": "List of model information"},
    )
    total: int = field(
        default=0,
        metadata={"description": "Total number of models"},
    )


@dataclass
class RunResponse:
    """Response for running a benchmark."""
    benchmark: BenchmarkResult = field(
        metadata={"description": "Benchmark result"}
    )
    
    @property
    def success(self) -> bool:
        """Check if benchmark completed successfully."""
        return self.benchmark.summary.get("success", False)


@dataclass
class EngineSaveResponse:
    """Response for saving an engine."""
    engine: EngineInfo = field(
        metadata={"description": "Saved engine information"}
    )
    
    @property
    def success(self) -> bool:
        """Check if save was successful."""
        return self.engine is not None


@dataclass
class EngineUpdateResponse:
    """Response for updating an engine."""
    engine: EngineInfo = field(
        metadata={"description": "Updated engine information"}
    )
    
    @property
    def success(self) -> bool:
        """Check if update was successful."""
        return self.engine is not None


@dataclass
class TaskListResponse:
    """Response for listing tasks."""
    tasks: List[Dict[str, Any]] = field(
        default_factory=list,
        metadata={"description": "List of tasks"},
    )
    total: int = field(
        default=0,
        metadata={"description": "Total number of tasks"},
    )


@dataclass
class ResultsResponse:
    """Response for retrieving benchmark results."""
    results: Dict[str, Any] = field(
        metadata={"description": "Benchmark results data"}
    )
    
    @property
    def success(self) -> bool:
        """Check if results retrieval was successful."""
        return self.results.get("success", False)


@dataclass
class EngineStatusResponse:
    """Response for engine status."""
    status: str = field(metadata={"description": "Engine status"})
    message: str = field(metadata={"description": "Status message"})


@dataclass
class ErrorResponse:
    """Standard error response format."""
    code: int = field(metadata={"description": "HTTP status code"})
    message: str = field(metadata={"description": "Error message"})
    details: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Additional error details"},
    )
    
    @property
    def success(self) -> bool:
        """Check if response indicates success."""
        return self.code == 200


@dataclass
class HealthResponse:
    """Health check response."""
    status: str = field(metadata={"description": "Health status"})
    version: str = field(metadata={"description": "Application version"})
    timestamp: datetime = field(metadata={"description": "Check timestamp"})


__all__ = [
    "ModelInfo",
    "EngineInfo",
    "Usage",
    "Choice",
    "LLMResponse",
    "EngineResult",
    "BenchmarkResult",
    "EngineListResponse",
    "EngineDetailResponse",
    "ModelListResponse",
    "RunResponse",
    "EngineSaveResponse",
    "EngineUpdateResponse",
    "TaskListResponse",
    "ResultsResponse",
    "EngineStatusResponse",
    "ErrorResponse",
    "HealthResponse",
]
