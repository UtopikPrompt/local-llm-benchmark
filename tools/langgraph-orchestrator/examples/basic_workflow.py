"""Example basic workflow script."""

import asyncio
from langgraph_orchestrator import Orchestrator
from langgraph_orchestrator.graph.workflow import OrchestrationWorkflow


async def main() -> None:
    """Run a basic orchestration workflow."""
    # Create orchestrator
    orchestrator = Orchestrator()

    # Create workflow
    workflow = OrchestrationWorkflow()

    # Run planning stage
    await workflow.run("planning", "./engine", orchestrator)

    # Run coding stage
    await workflow.run("coding", "./engine", orchestrator)

    # Run validation stage
    await workflow.run("validation", "./engine", orchestrator)

    # Run testing stage
    await workflow.run("testing", "./engine", orchestrator)

    print("Workflow completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
