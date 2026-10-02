"""Base agent class for hierarchical orchestration with LangGraph integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """Message format for agent communication."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: str
    receiver: str
    content: Any
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from agent operations."""

    success: bool
    content: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all orchestration agents."""

    def __init__(
        self,
        name: str,
        description: str = "",
        config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.config = config or {}
        self.id = str(uuid4())
        self.history: list[AgentMessage] = []
        self._handlers: dict[str, Callable[[Any], AgentResponse]] = {}

    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentResponse:
        """Process an incoming message and return a response."""
        pass

    async def send_message(
        self,
        receiver: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """Create and store a message to send to another agent."""
        from datetime import datetime

        message = AgentMessage(
            sender=self.name,
            receiver=receiver,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {},
        )
        self.history.append(message)
        return message

    def register_handler(
        self, message_type: str, handler: Callable[[Any], AgentResponse]
    ) -> None:
        """Register a handler for a specific message type."""
        self._handlers[message_type] = handler

    def _create_response(
        self, success: bool, content: Any = None, error: str | None = None
    ) -> AgentResponse:
        """Create a standardized response."""
        return AgentResponse(success=success, content=content, error=error)

    @property
    def state(self) -> dict[str, Any]:
        """Get the current state of the agent."""
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "history_length": len(self.history),
        }

    async def execute_task(self, task: dict[str, Any]) -> AgentResponse:
        """Execute a task with the agent."""
        task_type = task.get("type", "default")
        task_data = task.get("data", {})

        if task_type in self._handlers:
            return await self._handlers[task_type](task_data)

        return self._create_response(
            success=False, error=f"Unknown task type: {task_type}"
        )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, id={self.id[:8]})"
