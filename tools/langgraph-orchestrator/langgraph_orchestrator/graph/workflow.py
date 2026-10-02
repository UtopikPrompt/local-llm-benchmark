"""LangGraph workflow definitions for orchestration."""

from __future__ import annotations

from typing import Any


class OrchestrationWorkflow:
    """LangGraph-based workflow for autonomous project coding."""

    def __init__(self) -> None:
        self.stages: dict[str, Any] = {}

    async def run(self, workflow_name: str, target: str, orchestrator: Any) -> None:
        """Run the specified workflow."""
        if workflow_name == "planning":
            await self.run_planning(target, orchestrator)
        elif workflow_name == "coding":
            await self.run_coding(target, orchestrator)
        elif workflow_name == "validation":
            await self.run_validation(target, orchestrator)
        elif workflow_name == "testing":
            await self.run_testing(target, orchestrator)

    async def run_all(self, target: str, orchestrator: Any) -> None:
        """Run all orchestration stages."""
        stages = ["planning", "coding", "validation", "testing"]
        for stage in stages:
            await self.run(stage, target, orchestrator)

    async def run_planning(self, target: str, orchestrator: Any) -> None:
        """Run the planning stage."""
        project_agent = orchestrator.get_agent("project")

        # Analyze project structure
        message = await project_agent.send_message(
            receiver="project",
            content={"type": "analyze", "target": target}
        )
        response = await project_agent.process(message)

        self.stages["planning"] = response.content

    async def run_coding(self, target: str, orchestrator: Any) -> None:
        """Run the coding stage."""
        coding_agent = orchestrator.get_agent("coding")

        # Generate code
        message = await coding_agent.send_message(
            receiver="coding",
            content={"type": "generate", "target": target}
        )
        response = await coding_agent.process(message)

        self.stages["coding"] = response.content

    async def run_validation(self, target: str, orchestrator: Any) -> None:
        """Run the validation stage."""
        review_agent = orchestrator.get_agent("review")

        # Review code
        message = await review_agent.send_message(
            receiver="review",
            content={"type": "review", "target": target}
        )
        response = await review_agent.process(message)

        self.stages["validation"] = response.content

    async def run_testing(self, target: str, orchestrator: Any) -> None:
        """Run the testing stage."""
        testing_agent = orchestrator.get_agent("testing")

        # Run tests
        message = await testing_agent.send_message(
            receiver="testing",
            content={"type": "run", "target": target}
        )
        response = await testing_agent.process(message)

        self.stages["testing"] = response.content
