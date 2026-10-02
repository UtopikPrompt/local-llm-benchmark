"""System-level orchestration agent."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class SystemAgent(BaseAgent):
    """Top-level orchestration agent that coordinates all other agents."""

    def __init__(self) -> None:
        super().__init__(
            name="system",
            description="System-level orchestration agent that coordinates all other agents",
        )

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Process an incoming message and delegate to appropriate agent."""
        content = message.content
        if isinstance(content, dict):
            task_type = content.get("type", "default")
            if task_type == "orchestrate":
                return self._orchestrate(content)
        return self._create_response(success=True, content="System agent processed message")

    def _orchestrate(self, data: dict[str, Any]) -> AgentResponse:
        """Orchestrate multiple agents to complete a task."""
        # This would coordinate multiple agents
        return self._create_response(
            success=True, content={"status": "orchestrating", "agents": ["project", "coding", "review", "testing"]}
        )
