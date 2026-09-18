"""Engine configuration and result schemas.

These dataclasses define the contract for LLM engine operations,
including configuration parameters and result structures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EngineConfig:
    """Configuration for an LLM engine.
    
    This configuration encapsulates all settings required to initialize
    and operate an LLM engine, including network settings, model parameters,
    and execution options.
    
    Attributes:
        model: The LLM model identifier (e.g., "llama3:8b",
               "gpt-4o-mini")
        base_url: Optional base URL for the API endpoint
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature for randomness
        top_p: Nucleus sampling probability threshold
        max_requests: Maximum concurrent requests allowed
        max_body_size: Maximum request body size in bytes
        max_headers_size: Maximum headers size in bytes
        max_response_size: Maximum response size in bytes
        max_keepalive_connections: Maximum keep-alive connections
        keepalive_timeout: Keep-alive timeout in seconds
        extra_headers: Additional headers to include in requests
    """
    model: str = field(default="", metadata={"description": "LLM model identifier"})
    base_url: Optional[str] = field(default=None, metadata={"description": "API base URL"})
    max_tokens: int = field(default=4096, metadata={"description": "Maximum tokens to generate"})
    temperature: float = field(default=0.7, metadata={"description": "Sampling temperature"})
    top_p: float = field(default=0.9, metadata={"description": "Nucleus sampling threshold"})
    max_requests: int = field(default=20, metadata={"description": "Max concurrent requests"})
    max_body_size: int = field(default=8 * 1024 * 1024, metadata={"description": "Max request body (8MB)"})
    max_headers_size: int = field(default=1 * 1024 * 1024, metadata={"description": "Max headers (1MB)"})
    max_response_size: int = field(default=8 * 1024 * 1024, metadata={"description": "Max response (8MB)"})
    max_keepalive_connections: int = field(
        default=400, 
        metadata={"description": "Max keep-alive connections"}
    )
    keepalive_timeout: int = field(
        default=300, 
        metadata={"description": "Keep-alive timeout (seconds)"}
    )
    extra_headers: Dict[str, str] = field(
        default_factory=dict, 
        metadata={"description": "Additional request headers"}
    )
    # HTTP Client Configuration
    max_connections: int = field(
        default=100, 
        metadata={"description": "Maximum concurrent connections"}
    )
    keepalive_connections: int = field(
        default=50, 
        metadata={"description": "Maximum keep-alive connections"}
    )
    timeout: float = field(
        default=60.0, 
        metadata={"description": "Request timeout in seconds"}
    )
    max_retries: int = field(
        default=3, 
        metadata={"description": "Maximum retry attempts on failure"}
    )
    retry_backoff: str = field(
        default="exponential", 
        metadata={"description": "Retry backoff strategy: exponential or linear"}
    )
    retry_backoff_max: float = field(
        default=60.0, 
        metadata={"description": "Maximum retry delay in seconds"}
    )


@dataclass
class EngineResult:
    """Result of an LLM engine operation.
    
    This structure encapsulates the complete response from an LLM engine,
    including the generated text, metadata, and any errors that occurred.
    
    Attributes:
        output: The generated text response
        usage: Token usage statistics (input, output, total)
        errors: List of any errors encountered during generation
        metadata: Additional metadata about the request/response
    """
    output: Optional[str] = field(default=None, metadata={"description": "Generated text"})
    usage: Optional[Dict[str, int]] = field(default=None, metadata={"description": "Token usage statistics"})
    errors: List[Dict[str, Any]] = field(default_factory=list, metadata={"description": "Errors encountered"})
    metadata: Optional[Dict[str, Any]] = field(default=None, metadata={"description": "Additional metadata"})
