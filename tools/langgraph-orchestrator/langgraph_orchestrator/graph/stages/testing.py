"""Testing stage for orchestration."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class TestingStage:
    """Testing stage that runs tests and validates functionality."""

    def __init__(self) -> None:
        self.name = "testing"
        self.description = "Runs tests and validates functionality"

    async def execute(self, testing_agent: BaseAgent, code: dict[str, Any]) -> dict[str, Any]:
        """Execute the testing stage."""
        # Run tests
        message = AgentMessage(
            sender="testing_stage",
            receiver="testing",
            content={"type": "run", "code": code}
        )

        response = await testing_agent.process(message)

        return {
            "stage": self.name,
            "success": response.success,
            "content": response.content,
            "timestamp": response.timestamp
        }
