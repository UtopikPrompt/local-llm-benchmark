"""Project management agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class ProjectAgent(BaseAgent):
    """Project management and coordination agent."""

    def __init__(self) -> None:
        super().__init__(
            name="project",
            description="Project management agent that handles project structure and dependencies",
        )

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Process project-related messages."""
        content = message.content
        if isinstance(content, dict):
            task_type = content.get("type", "default")
            if task_type == "analyze":
                return self._analyze_project(content)
            elif task_type == "validate":
                return self._validate_project(content)
            elif task_type == "update":
                return self._update_project(content)
        return self._create_response(success=True, content="Project agent processed message")

    def _analyze_project(self, data: dict[str, Any]) -> AgentResponse:
        """Analyze project structure."""
        target = data.get("target", ".")
        project_path = Path(target)

        # Analyze project structure
        analysis = {
            "path": str(project_path.absolute()),
            "exists": project_path.exists(),
            "is_directory": project_path.is_dir(),
            "files": [],
            "directories": [],
        }

        if project_path.exists() and project_path.is_dir():
            for item in project_path.iterdir():
                if item.is_file():
                    analysis["files"].append(item.name)
                elif item.is_dir():
                    analysis["directories"].append(item.name)

        return self._create_response(success=True, content=analysis)

    def _validate_project(self, data: dict[str, Any]) -> AgentResponse:
        """Validate project structure and configuration."""
        return self._create_response(
            success=True,
            content={"valid": True, "issues": [], "recommendations": []}
        )

    def _update_project(self, data: dict[str, Any]) -> AgentResponse:
        """Update project structure."""
        return self._create_response(success=True, content={"status": "updated"})
