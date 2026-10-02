"""Main orchestrator class for LangGraph-based autonomous project coding."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from langgraph_orchestrator.agents.base import BaseAgent
from langgraph_orchestrator.agents.system_agent import SystemAgent
from langgraph_orchestrator.agents.project_agent import ProjectAgent
from langgraph_orchestrator.agents.coding_agent import CodingAgent
from langgraph_orchestrator.agents.review_agent import ReviewAgent
from langgraph_orchestrator.agents.testing_agent import TestingAgent
from langgraph_orchestrator.graph.workflow import OrchestrationWorkflow


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    target_directory: str = "."
    log_level: str = "INFO"
    enable_debug: bool = False


class OrchestratorState:
    """State management for the orchestrator."""

    def __init__(self) -> None:
        self.current_stage: str = "idle"
        self.progress: dict[str, Any] = {}
        self.completed_stages: list[str] = []
        self.errors: list[str] = []

    def update_stage(self, stage: str) -> None:
        """Update the current stage."""
        self.current_stage = stage

    def record_completion(self, stage: str) -> None:
        """Record a completed stage."""
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)

    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)


class Orchestrator:
    """Main orchestrator class for LangGraph-based autonomous project coding."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self.state = OrchestratorState()
        self.agents: dict[str, BaseAgent] = {}
        self._create_agents()

    def _create_agents(self) -> None:
        """Create all agents for the orchestration system."""
        self.agents["system"] = SystemAgent()
        self.agents["project"] = ProjectAgent()
        self.agents["coding"] = CodingAgent()
        self.agents["review"] = ReviewAgent()
        self.agents["testing"] = TestingAgent()

    async def run_workflow(self, workflow_name: str, target: str) -> None:
        """Run a specific workflow."""
        self.state.update_stage(workflow_name)
        workflow = OrchestrationWorkflow(self)
        await workflow.run(workflow_name, target)

    async def run_all(self, target: str) -> None:
        """Run all orchestration stages."""
        stages = ["planning", "coding", "validation", "testing"]
        for stage in stages:
            await self.run_workflow(stage, target)
            self.state.record_completion(stage)

    def get_agent(self, name: str) -> BaseAgent:
        """Get an agent by name."""
        if name not in self.agents:
            raise ValueError(f"Agent not found: {name}")
        return self.agents[name]

    def get_state(self) -> dict[str, Any]:
        """Get the current state of the orchestrator."""
        return {
            "current_stage": self.state.current_stage,
            "completed_stages": self.state.completed_stages,
            "errors": self.state.errors,
            "agents": {name: agent.state for name, agent in self.agents.items()},
        }
