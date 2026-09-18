"""Local LLM Benchmark package.

This package provides the core functionality for benchmarking Large Language Models.
Includes modules for:
- Configuration management
- Engine interface and implementations
- Benchmark execution and metrics
- Error handling and retry logic
- Caching strategies
- Structured logging
- Report generation
"""

from .config import Config
from .di import (
    DependencyContainer,
    DependencyError,
    DependencyResolutionError,
    DependencyCreationError,
    DependencyLookupError,
    DependencyNotBoundError,
)
from .errors import (
    BenchmarkError,
    DatabaseError,
    LLMError,
    PermanentError,
    RetryableError,
    TransientError,
    BenchmarkValidationError,
    DatabaseValidationError,
    LLMValidationError,
    LLMTimeoutError,
    LLMConnectionError,
    DatabaseConnectionError,
)
from .logger import BenchmarkLogger, logger
from .metrics import BenchmarkMetrics, MetricsCollector
from .runner import BenchmarkRunner, run_benchmark
from .report import generate_report
from .utils.retry import retry, RetryConfig

__version__ = "0.1.0"
__all__ = [
    "Config",
    "BenchmarkLogger",
    "logger",
    "BenchmarkMetrics",
    "MetricsCollector",
    "BenchmarkRunner",
    "run_benchmark",
    "generate_report",
    "retry",
    "RetryConfig",
]
