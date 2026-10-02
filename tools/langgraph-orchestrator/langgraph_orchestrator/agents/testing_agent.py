"""Testing agent."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class TestingAgent(BaseAgent):
    """Testing and validation agent."""

    def __init__(self) -> None:
        super().__init__(
            name="testing",
            description="Testing agent that runs tests and validates functionality",
        )

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Process testing-related messages."""
        content = message.content
        if isinstance(content, dict):
            task_type = content.get("type", "default")
            if task_type == "run":
                return self._run_tests(content)
            elif task_type == "validate":
                return self._validate_tests(content)
        return self._create_response(success=True, content="Testing agent processed message")

    def _run_tests(self, data: dict[str, Any]) -> AgentResponse:
        """Run tests."""
        target = data.get("target", ".")

        # Simulate test execution
        test_results = {
            "total": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "coverage": 85.0,
        }

        return self._create_response(success=True, content=test_results)

    def _validate_tests(self, data: dict[str, Any]) -> AgentResponse:
        """Validate test coverage."""
        return self._create_response(success=True, content={"coverage": "good", "threshold": 80})
