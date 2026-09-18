"""Unified error handling for local-llm-benchmark."""

from typing import Optional
from pydantic import ValidationError
from httpx import RequestError, TimeoutException


class BenchmarkError(Exception):
    """Base exception for benchmark errors."""
    pass


class LLMError(BenchmarkError):
    """LLM-related errors."""
    pass


class DatabaseError(BenchmarkError):
    """Database-related errors."""
    pass


class PermanentError(BenchmarkError, RetryableError):
    """Permanent errors that should not be retried."""
    pass


class RetryableError(Exception):
    """Errors that should be retried."""
    pass


class TransientError(BenchmarkError, RetryableError):
    """Transient errors like timeouts, 500s, network issues."""
    pass


# Convenience exceptions for common error scenarios
class LLMTimeoutError(LLMError, TransientError):
    """LLM request timeout."""
    pass


class LLMConnectionError(LLMError, TransientError):
    """LLM connection failure."""
    pass


class LLMValidationError(LLMError, PermanentError):
    """Invalid LLM request validation error."""
    pass


class DatabaseConnectionError(DatabaseError, TransientError):
    """Database connection failure."""
    pass


class DatabaseValidationError(DatabaseError, PermanentError):
    """Invalid database operation error."""
    pass


class BenchmarkValidationError(BenchmarkError, PermanentError):
    """Invalid benchmark configuration or data."""
    pass


class ConfigurationError(BenchmarkError):
    """Configuration file or parameter errors."""
    pass


class EngineError(BenchmarkError):
    """Engine-specific errors."""
    pass


class ResultError(BenchmarkError):
    """Result processing and serialization errors."""
    pass


class ReportError(BenchmarkError):
    """Report generation errors."""
    pass


class CacheError(BenchmarkError):
    """Cache-related errors."""
    pass


class MetricsError(BenchmarkError):
    """Metrics collection and processing errors."""
    pass


class RunnerError(BenchmarkError):
    """Benchmark runner errors."""
    pass


class ServiceError(BenchmarkError):
    """Service layer errors."""
    pass


class APIError(BenchmarkError):
    """API communication errors."""
    pass


class HTTPError(BenchmarkError):
    """HTTP-related errors."""
    pass


class ValidationError(BenchmarkError):
    """Data validation errors."""
    pass


class TimeoutError(BenchmarkError, TransientError):
    """Operation timeout errors."""
    pass


class ResourceError(BenchmarkError):
    """Resource exhaustion errors."""
    pass


class NetworkError(BenchmarkError, TransientError):
    """Network connectivity errors."""
    pass


class ValidationError(BenchmarkError, PermanentError):
    """Data format or schema validation errors."""
    pass


class EngineNotFoundError(BenchmarkError):
    """Requested engine not found."""
    pass


class EngineConfigError(BenchmarkError):
    """Engine configuration errors."""
    pass


class EngineConnectionError(BenchmarkError, TransientError):
    """Failed to connect to engine."""
    pass


class EngineBenchmarkError(BenchmarkError):
    """Engine benchmark execution errors."""
    pass


class BenchmarkTimeoutError(BenchmarkError, TransientError):
    """Benchmark execution timeout."""
    pass


class BenchmarkValidationError(BenchmarkError, PermanentError):
    """Invalid benchmark configuration or data."""
    pass


class CacheMissError(BenchmarkError):
    """Cache miss or cache invalidation errors."""
    pass


class MetricsCollectionError(BenchmarkError):
    """Metrics collection failures."""
    pass


class ReportGenerationError(BenchmarkError):
    """Report generation failures."""
    pass


class RunnerExecutionError(BenchmarkError):
    """Benchmark runner execution errors."""
    pass


class ServiceUnavailableError(BenchmarkError, TransientError):
    """Service temporarily unavailable."""
    pass


class APIConnectionError(BenchmarkError, TransientError):
    """API connection failures."""
    pass


class HTTPTimeoutError(HTTPError, TransientError):
    """HTTP request timeout."""
    pass


class HTTPConnectionError(HTTPError, TransientError):
    """HTTP connection failure."""
    pass


class HTTPValidationError(HTTPError, PermanentError):
    """HTTP response validation error."""
    pass


class ValidationError(BenchmarkError, PermanentError):
    """Data validation errors."""
    pass


class EngineExecutionError(BenchmarkError):
    """Engine execution errors."""
    pass


class EngineTimeoutError(BenchmarkError, TransientError):
    """Engine operation timeout."""
    pass


class EngineValidationError(BenchmarkError, PermanentError):
    """Engine validation errors."""
    pass


class BenchmarkExecutionError(BenchmarkError):
    """Benchmark execution errors."""
    pass


class BenchmarkTimeoutError(BenchmarkError, TransientError):
    """Benchmark timeout errors."""
    pass


class BenchmarkConnectionError(BenchmarkError, TransientError):
    """Benchmark connection errors."""
    pass


class ResultValidationError(BenchmarkError, PermanentError):
    """Result validation errors."""
    pass


class ResultSerializationError(ResultError):
    """Result serialization failures."""
    pass


class ReportSerializationError(ReportError):
    """Report serialization failures."""
    pass


class CacheSerializationError(CacheError):
    """Cache serialization failures."""
    pass


class MetricValidationError(MetricsError):
    """Metric validation errors."""
    pass


class MetricsValidationError(MetricsError, PermanentError):
    """Metric validation errors."""
    pass


class RunnerValidationError(RunnerError):
    """Runner validation errors."""
    pass


class RunnerExecutionError(RunnerError):
    """Runner execution errors."""
    pass


class RunnerTimeoutError(RunnerError, TransientError):
    """Runner timeout errors."""
    pass


class ServiceValidationError(ServiceError):
    """Service validation errors."""
    pass


class APIDeprecationWarning(BenchmarkError):
    """API deprecation warnings."""
    pass


class APIError(BenchmarkError):
    """API errors."""
    pass


class APIValidationError(APIError, PermanentError):
    """API validation errors."""
    pass


class APITimeoutError(APIError, TransientError):
    """API timeout errors."""
    pass


class APINotFoundError(APIError):
    """API endpoint not found."""
    pass


class APIServerError(APIError, TransientError):
    """API server errors."""
    pass
