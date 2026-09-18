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


class RetryableError(BenchmarkError):
    """Errors that should be retried."""
    pass


class TransientError(RetryableError):
    """Transient errors like timeouts, 500s, network issues."""
    pass


class PermanentError(RetryableError):
    """Permanent errors that should not be retried."""
    pass


class DependencyError(Exception):
    """Base exception for dependency errors."""
    pass


class DependencyResolutionError(DependencyError):
    """Error when a dependency cannot be resolved."""
    pass


class DependencyCreationError(DependencyError):
    """Error when creating a dependency instance."""
    pass


class DependencyLookupError(DependencyError):
    """Error when looking up a dependency."""
    pass


class DependencyNotBoundError(DependencyError):
    """Error when a dependency is not bound to the container."""
    pass


class BenchmarkValidationError(Exception):
    """Validation errors for benchmark configuration and data."""
    pass


class DatabaseValidationError(BenchmarkValidationError):
    """Validation errors for database configuration and operations."""
    pass


class LLMValidationError(BenchmarkValidationError):
    """Validation errors for LLM configuration and operations."""
    pass


class LLMTimeoutError(BenchmarkError):
    """LLM-specific timeout errors."""
    pass


class LLMConnectionError(BenchmarkError):
    """LLM connection errors."""
    pass


class DatabaseConnectionError(BenchmarkError):
    """Database connection errors."""
    pass


class DependencyError(Exception):
    """Base exception for dependency errors."""
    pass


class DependencyResolutionError(DependencyError):
    """Error when a dependency cannot be resolved."""
    pass


class DependencyCreationError(DependencyError):
    """Error when creating a dependency instance."""
    pass


class DependencyLookupError(DependencyError):
    """Error when looking up a dependency."""
    pass


class DependencyNotBoundError(DependencyError):
    """Error when a dependency is not bound to the container."""
    pass
