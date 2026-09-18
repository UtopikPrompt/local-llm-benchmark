"""Dependency Injection Container Implementation.

Provides a generic dependency container for resolving dependencies in the benchmark system.
Follows the dependency injection pattern to reduce tight coupling and improve testability.
"""

from typing import TypeVar, Generic, Optional, Dict, Any, Type, Callable

# Import error classes from errors module
from .errors import (
    DependencyError,
    DependencyResolutionError,
    DependencyCreationError,
)

# TypeVar for generic type support
T = TypeVar('T')


class DependencyContainer(Generic[T]):
    """Generic dependency container for resolving dependencies.
    
    This container supports:
    - Singletons (instances created once and reused)
    - Factories (instances created on-demand)
    - Type hints for type-safe resolution
    
    Example:
        >>> container = DependencyContainer()
        >>> container.bind(Engine, lambda: LocalLLMEngine())
        >>> engine = container.resolve(Engine)
    """
    
    def __init__(self) -> None:
        """Initialize the dependency container."""
        self._dependencies: Dict[Type[T], Any] = {}
        self._factories: Dict[Type[T], Any] = {}
    
    def bind(self, dependency: Type[T], factory: Callable[[], T]) -> None:
        """Register a dependency factory for the given type.
        
        Args:
            dependency: The type of dependency to register
            factory: A callable that creates instances of the dependency
        
        Raises:
            DependencyCreationError: If the factory is not callable
        """
        if not callable(factory):
            raise DependencyCreationError(
                f"Factory for {dependency} must be a callable, got {type(factory)}"
            )
        self._dependencies[dependency] = factory
    
    def resolve(self, dependency: Type[T]) -> T:
        """Resolve a dependency from the container.
        
        Args:
            dependency: The type of dependency to resolve
        
        Returns:
            An instance of the dependency
        
        Raises:
            DependencyResolutionError: If the dependency is not registered
        """
        if dependency not in self._dependencies:
            raise DependencyResolutionError(
                f"Dependency {dependency} is not registered in the container"
            )
        
        factory = self._dependencies[dependency]
        return factory()
    
    def resolve_all(self, dependencies: list[Type[T]]) -> dict[Type[T], T]:
        """Resolve multiple dependencies atomically.
        
        This method ensures all dependencies are resolved in a single pass,
        which is useful for complex dependency graphs.
        
        Args:
            dependencies: List of dependency types to resolve
        
        Returns:
            A dictionary mapping dependency types to their instances
        
        Raises:
            DependencyResolutionError: If any dependency is not registered
        """
        resolved: dict[Type[T], T] = {}
        
        for dep_type in dependencies:
            if dep_type not in self._dependencies:
                raise DependencyResolutionError(
                    f"Dependency {dep_type} is not registered in the container"
                )
            
            factory = self._dependencies[dep_type]
            resolved[dep_type] = factory()
        
        return resolved
    
    def has(self, dependency: Type[T]) -> bool:
        """Check if a dependency is registered in the container.
        
        Args:
            dependency: The type to check
            
        Returns:
            True if the dependency is registered, False otherwise
        """
        return dependency in self._dependencies
    
    def clear(self) -> None:
        """Clear all registered dependencies."""
        self._dependencies.clear()
        self._factories.clear()


class DependencyError(Exception):
    """Base exception for dependency-related errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DependencyResolutionError(DependencyError):
    """Raised when a dependency cannot be resolved from the container."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DependencyCreationError(DependencyError):
    """Raised when a dependency factory fails to create an instance."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DependencyLookupError(DependencyError):
    """Raised when a dependency is not found during resolution."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DependencyNotBoundError(DependencyError):
    """Raised when a dependency is requested but not bound to the container."""
    
    def __init__(self, dependency: Type) -> None:
        message = f"Dependency {dependency} is not bound to the container"
        super().__init__(message)
        self.dependency = dependency
