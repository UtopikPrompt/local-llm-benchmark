"""Validation stage for orchestration."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class ValidationStage:
    """Validation stage that reviews and validates code quality."""

    def __init__(self) -> None:
        self.name = "validation"
        self.description = "Reviews and validates code quality"

    async def execute(self, review_agent: BaseAgent, code: dict[str, Any]) -> dict[str, Any]:
        """Execute the validation stage."""
        # Review code
        message = AgentMessage(
            sender="validation_stage",
            receiver="review",
            content={"type": "review", "code": code}
        )

        response = await review_agent.process(message)

        return {
            "stage": self.name,
            "success": response.success,
            "content": response.content,
            "timestamp": response.timestamp
        }
