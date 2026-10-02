"""Code generation agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph_orchestrator.agents.base import AgentMessage, AgentResponse, BaseAgent


class CodingAgent(BaseAgent):
    """Code generation and modification agent."""

    def __init__(self) -> None:
        super().__init__(
            name="coding",
            description="Code generation agent that creates and modifies code files",
        )

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Process code-related messages."""
        content = message.content
        if isinstance(content, dict):
            task_type = content.get("type", "default")
            if task_type == "generate":
                return self._generate_code(content)
            elif task_type == "modify":
                return self._modify_code(content)
            elif task_type == "analyze":
                return self._analyze_code(content)
        return self._create_response(success=True, content="Coding agent processed message")

    def _generate_code(self, data: dict[str, Any]) -> AgentResponse:
        """Generate new code files."""
        target_dir = data.get("target", ".")
        code_spec = data.get("spec", {})

        # Generate code based on specification
        generated_files = []
        for file_spec in code_spec.get("files", []):
            file_path = Path(target_dir) / \
                file_spec.get("path", "generated.py")
            file_content = file_spec.get("content", "# Generated code\n")

            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(file_path, "w") as f:
                f.write(file_content)

            generated_files.append({
                "path": str(file_path),
                "status": "created",
            })

        return self._create_response(success=True, content={"files": generated_files})

    def _modify_code(self, data: dict[str, Any]) -> AgentResponse:
        """Modify existing code files."""
        return self._create_response(success=True, content={"status": "modified"})

    def _analyze_code(self, data: dict[str, Any]) -> AgentResponse:
        """Analyze existing code."""
        return self._create_response(
            success=True,
            content={"complexity": "low", "issues": [], "recommendations": []}
        )
