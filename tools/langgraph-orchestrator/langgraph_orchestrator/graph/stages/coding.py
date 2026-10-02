"""Coding stage for orchestration."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class CodingStage:
    """Coding stage that generates code based on requirements."""

    def __init__(self) -> None:
        self.name = "coding"
        self.description = "Generates code based on requirements"

    async def execute(self, coding_agent: BaseAgent, requirements: dict[str, Any]) -> dict[str, Any]:
        """Execute the coding stage."""
        # Generate code
        message = AgentMessage(
            sender="coding_stage",
            receiver="coding",
            content={"type": "generate", "requirements": requirements}
        )

        response = await coding_agent.process(message)

        return {
            "stage": self.name,
            "success": response.success,
            "content": response.content,
            "timestamp": response.timestamp
        }
