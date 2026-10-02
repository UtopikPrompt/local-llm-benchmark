# LangGraph Orchestration System

Hierarchical orchestration system with LangGraph for autonomous project coding.

## Overview

This tool provides a multi-layer orchestration system that enables autonomous development of the local-llm-benchmark project through coordinated agents and LangGraph-based workflow management.

## Architecture

```
LangGraph Orchestration System
├── Manager (orchestrator.py)      - Main orchestration coordinator
├── Agents (agents/)               - Hierarchical agent system
│   ├── base.py                    - Base agent class
│   ├── system.py                  - System-level orchestration agent
│   ├── project.py                 - Project management agent
│   ├── coding.py                  - Code generation agent
│   ├── review.py                  - Code review agent
│   └── testing.py                 - Testing agent
└── Graph (graph/)                 - LangGraph workflow definitions
    ├── workflow.py                - Main workflow graph
    └── stages/                    - Orchestration stages
        ├── planning.py
        ├── coding.py
        ├── validation.py
        └── testing.py
```

## Installation

```bash
cd tools/langgraph-orchestrator
pip install -e .
```

## Usage

```bash
# Start the orchestration system
python -m langgraph_orchestrator

# Run a specific workflow
python -m langgraph_orchestrator run <workflow_name>
```

## Agent Hierarchy

- **SystemAgent**: Top-level orchestration, coordinates all other agents
- **ProjectAgent**: Manages project structure and dependencies
- **CodingAgent**: Generates and modifies code files
- **ReviewAgent**: Reviews code quality and adherence to standards
- **TestingAgent**: Runs tests and validates functionality
