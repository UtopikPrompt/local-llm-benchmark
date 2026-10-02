"""Planning stage for orchestration."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class PlanningStage:
    """Planning stage that analyzes project structure and requirements."""

    def __init__(self) -> None:
        self.name = "planning"
        self.description = "Analyzes project structure and requirements"

    async def execute(self, project_agent: BaseAgent, target: str) -> dict[str, Any]:
        """Execute the planning stage."""
        # Analyze project structure
        message = AgentMessage(
            sender="planning_stage",
            receiver="project",
            content={"type": "analyze", "target": target}
        )

        response = await project_agent.process(message)

        return {
            "stage": self.name,
            "success": response.success,
            "content": response.content,
            "timestamp": response.timestamp
        }
