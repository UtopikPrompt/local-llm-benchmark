"""
Agent hierarchy for hierarchical orchestration.

This module defines the agent hierarchy for the orchestration system:
- BaseAgent: Abstract base class for all agents
- SystemAgent: Top-level orchestration agent
- ProjectAgent: Project management and coordination
- CodingAgent: Code generation and modification
- ReviewAgent: Code review and validation
- TestingAgent: Testing and validation
"""

from __future__ import annotations

from app.orchestrator.agents.base import BaseAgent
from app.orchestrator.agents.system_agent import SystemAgent
from app.orchestrator.agents.project_agent import ProjectAgent
from app.orchestrator.agents.coding_agent import CodingAgent
from app.orchestrator.agents.review_agent import ReviewAgent
from app.orchestrator.agents.testing_agent import TestingAgent

__all__ = [
    "BaseAgent",
    "SystemAgent",
    "ProjectAgent",
    "CodingAgent",
    "ReviewAgent",
    "TestingAgent",
]
