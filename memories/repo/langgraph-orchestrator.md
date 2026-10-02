# LangGraph Orchestration System

## Architecture

- **CLI Interface** - Command-line interface for interacting with the orchestration system
- **Orchestrator** - Main orchestrator class that coordinates agents and workflows
- **Agent Hierarchy** - 5 agents: System, Project, Coding, Review, Testing
- **LangGraph Workflow** - Workflow definitions with 4 stages: Planning, Coding, Validation, Testing

## Key Files

- `tools/langgraph-orchestrator/langgraph_orchestrator/cli.py` - CLI interface
- `tools/langgraph-orchestrator/langgraph_orchestrator/orchestrator.py` - Main orchestrator
- `tools/langgraph-orchestrator/langgraph_orchestrator/agents/` - Agent implementations
- `tools/langgraph-orchestrator/langgraph_orchestrator/graph/` - Workflow definitions

## Agent Pattern

Each agent implements the `BaseAgent` interface with:

- `process(message)` - Process incoming messages
- `send_message(receiver, content)` - Send messages to other agents
- `receive_message(sender, content)` - Handle incoming messages

## Workflow Pattern

The orchestration follows a hierarchical pattern:

1. **Top-Level Orchestration** - SystemAgent coordinates overall workflow
2. **Stage-Level Orchestration** - Each stage coordinates relevant agents
3. **Agent-Level Processing** - Each agent processes specific tasks

## Extensibility

- Add new agents by extending `BaseAgent`
- Add new stages by implementing the stage interface
- Customize workflows by extending `OrchestrationWorkflow`
