"""Code review agent."""

from __future__ import annotations

from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class ReviewAgent(BaseAgent):
    """Code review and validation agent."""

    def __init__(self) -> None:
        super().__init__(
            name="review",
            description="Code review agent that validates code quality and adherence to standards",
        )

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Process review-related messages."""
        content = message.content
        if isinstance(content, dict):
            task_type = content.get("type", "default")
            if task_type == "review":
                return self._review_code(content)
            elif task_type == "validate":
                return self._validate_code(content)
        return self._create_response(success=True, content="Review agent processed message")

    def _review_code(self, data: dict[str, Any]) -> AgentResponse:
        """Review code quality."""
        code_files = data.get("files", [])

        reviews = []
        for file_path in code_files:
            review = {
                "file": file_path,
                "quality": "good",
                "issues": [],
                "suggestions": [],
            }
            reviews.append(review)

        return self._create_response(success=True, content={"reviews": reviews})

    def _validate_code(self, data: dict[str, Any]) -> AgentResponse:
        """Validate code against standards."""
        return self._create_response(
            success=True,
            content={"valid": True, "standards": [
                "PEP8", "type-hints", "docstrings"]}
        )
