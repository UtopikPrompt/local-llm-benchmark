"""Core engine logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List


@dataclass
class EngineConfig:
    """Configuration for :class:`Engine`."""

    max_iterations: int = 100
    parallel: bool = False

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be a positive integer")


@dataclass
class StepResult:
    """Outcome produced by a single engine step."""

    name: str
    value: int
    ok: bool


class Engine:
    """A small processing engine that applies a pipeline of transform steps.

    Each step is a callable accepting the accumulated value and returning
    the next value. Steps run sequentially in registration order.
    """

    def __init__(self, config: EngineConfig | None = None) -> None:
        self.config = config or EngineConfig()
        self._steps: List[tuple[str, Callable[[int], int]]] = []

    def add_step(self, name: str, transform: Callable[[int], int]) -> "Engine":
        """Register a named transform step."""
        self._steps.append((name, transform))
        return self

    def run(self, seed: int = 0) -> list[StepResult]:
        """Run all registered steps starting from ``seed``."""
        if seed < 0:
            raise ValueError("seed must be non-negative")

        if len(self._steps) > self.config.max_iterations:
            raise ValueError(
                f"too many steps: {len(self._steps)} exceeds "
                f"max_iterations {self.config.max_iterations}"
            )

        value = seed
        results: List[StepResult] = []
        for name, transform in self._steps:
            value = transform(value)
            results.append(StepResult(name=name, value=value, ok=True))
        return results

    def fold(self, seed: int = 0) -> int:
        """Run all steps and return only the final accumulated value."""
        results = self.run(seed)
        return results[-1].value if results else seed

    def process(self, items: Iterable[int], seed: int = 0) -> List[int]:
        """Apply the pipeline to each input item."""
        return [self.fold(item) for item in items]