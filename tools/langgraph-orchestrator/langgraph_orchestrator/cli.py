"""Command-line interface for the LangGraph Orchestration System."""

from __future__ import annotations

import argparse
import asyncio
import sys

from langgraph_orchestrator import Orchestrator
from langgraph_orchestrator.graph.workflow import OrchestrationWorkflow


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="LangGraph Orchestration System for autonomous project coding"
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser(
        "run", help="Run an orchestration workflow")
    run_parser.add_argument(
        "workflow", choices=["all", "planning", "coding", "validation", "testing"],
        help="Workflow to run"
    )
    run_parser.add_argument(
        "--target", "-t", default=".",
        help="Target directory for the workflow"
    )

    # Status command
    subparsers.add_parser("status", help="Show current orchestration status")

    # List agents command
    subparsers.add_parser("agents", help="List available agents")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(run_workflow(args.workflow, args.target))
    elif args.command == "status":
        show_status()
    elif args.command == "agents":
        list_agents()
    else:
        parser.print_help()


async def run_workflow(workflow_name: str, target: str) -> None:
    """Run the specified workflow."""
    orchestrator = Orchestrator()
    workflow = OrchestrationWorkflow(orchestrator)

    if workflow_name == "all":
        await workflow.run_all(target)
    elif workflow_name == "planning":
        await workflow.run_planning(target)
    elif workflow_name == "coding":
        await workflow.run_coding(target)
    elif workflow_name == "validation":
        await workflow.run_validation(target)
    elif workflow_name == "testing":
        await workflow.run_testing(target)


def show_status() -> None:
    """Show current orchestration status."""
    print("LangGraph Orchestration System Status:")
    print("-----------------------------------")
    print("Agents: System, Project, Coding, Review, Testing")
    print("Workflows: planning, coding, validation, testing")
    print("Status: Ready")


def list_agents() -> None:
    """List available agents."""
    print("Available Agents:")
    print("-----------------")
    print("1. SystemAgent - Top-level orchestration")
    print("2. ProjectAgent - Project management")
    print("3. CodingAgent - Code generation")
    print("4. ReviewAgent - Code review")
    print("5. TestingAgent - Testing and validation")
