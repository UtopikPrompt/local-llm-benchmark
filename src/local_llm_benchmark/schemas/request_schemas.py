"""Request schemas for API endpoints.

These dataclasses define the request structures for all API endpoints,
providing type safety and validation for client requests.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnginePreviewRequest:
    """Request for previewing a candidate engine configuration.
    
    Used to test and validate engine configurations before saving.
    
    Attributes:
        base_url: The API base URL of the engine
        model: The model identifier to use
    """
    base_url: str = field(
        metadata={
            "description": "API base URL (e.g., http://localhost:8080/v1)",
            "example": "http://localhost:8080/v1",
        }
    )
    model: str = field(
        metadata={
            "description": "Model identifier (e.g., llama3:8b)",
            "example": "llama3:8b",
        }
    )


@dataclass
class ModelListRequest:
    """Request for listing models from an engine.
    
    Attributes:
        base_url: The API base URL of the engine
    """
    base_url: str = field(
        metadata={
            "description": "API base URL (e.g., http://localhost:8080/v1)",
            "example": "http://localhost:8080/v1",
        }
    )


@dataclass
class RunRequest:
    """Request for running a benchmark.
    
    Attributes:
        model: The model to benchmark
        max_tokens: Maximum tokens to generate per response
        timeout: Request timeout in seconds
    """
    model: str = field(
        metadata={
            "description": "Model identifier to benchmark",
            "example": "llama3:8b",
        }
    )
    max_tokens: int = field(
        metadata={
            "description": "Maximum tokens to generate per response",
            "default": 4096,
        }
    )
    timeout: int = field(
        metadata={
            "description": "Request timeout in seconds",
            "default": 120,
        }
    )


@dataclass
class EngineSaveRequest:
    """Request for saving a new engine configuration.
    
    Attributes:
        name: Unique identifier for the engine
        base_url: The API base URL of the engine
        model: The model identifier
    """
    name: str = field(
        metadata={
            "description": "Unique engine identifier",
            "example": "local-llama3",
        }
    )
    base_url: str = field(
        metadata={
            "description": "API base URL (e.g., http://localhost:8080/v1)",
            "example": "http://localhost:8080/v1",
        }
    )
    model: str = field(
        metadata={
            "description": "Model identifier (e.g., llama3:8b)",
            "example": "llama3:8b",
        }
    )


@dataclass
class EngineUpdateRequest:
    """Request for updating an existing engine configuration.
    
    Attributes:
        name: Unique identifier for the engine
        base_url: The API base URL of the engine
        model: The model identifier
    """
    name: str = field(
        metadata={
            "description": "Unique engine identifier",
            "example": "local-llama3",
        }
    )
    base_url: str = field(
        metadata={
            "description": "API base URL (e.g., http://localhost:8080/v1)",
            "example": "http://localhost:8080/v1",
        }
    )
    model: str = field(
        metadata={
            "description": "Model identifier (e.g., llama3:8b)",
            "example": "llama3:8b",
        }
    )


@dataclass
class EngineConfigRequest:
    """Request for engine configuration update.
    
    Attributes:
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling threshold
    """
    max_tokens: int = field(
        metadata={
            "description": "Maximum tokens to generate",
            "default": 4096,
        }
    )
    temperature: float = field(
        metadata={
            "description": "Sampling temperature",
            "default": 0.7,
        }
    )
    top_p: float = field(
        metadata={
            "description": "Nucleus sampling threshold",
            "default": 0.9,
        }
    )


@dataclass
class EngineListRequest:
    """Request for listing engines.
    
    Attributes:
        name: Filter by engine name
        base_url: Filter by base URL
    """
    name: Optional[str] = field(default=None)
    base_url: Optional[str] = field(default=None)


@dataclass
class EngineDetailRequest:
    """Request for engine detail retrieval."""
    name: str = field(
        metadata={
            "description": "Engine name to retrieve",
            "example": "local-llama3",
        }
    )


@dataclass
class TaskRequest:
    """Request for task corpus operations.
    
    Attributes:
        add: Tasks to add
        filter: Filter criteria
    """
    add: Optional[List[str]] = field(default=None)
    filter: Optional[Dict[str, Any]] = field(default=None)


@dataclass
class TaskListRequest:
    """Request for listing tasks."""
    filter: Optional[Dict[str, Any]] = field(default=None)


@dataclass
class ResultsRequest:
    """Request for retrieving benchmark results.
    
    Attributes:
        models: Comma-separated model names
        benchmark_type: Filter by benchmark type
    """
    models: Optional[str] = field(default=None)
    benchmark_type: Optional[str] = field(default=None)


__all__ = [
    "EnginePreviewRequest",
    "ModelListRequest",
    "RunRequest",
    "EngineSaveRequest",
    "EngineUpdateRequest",
    "EngineConfigRequest",
    "EngineListRequest",
    "EngineDetailRequest",
    "TaskRequest",
    "TaskListRequest",
    "ResultsRequest",
]
