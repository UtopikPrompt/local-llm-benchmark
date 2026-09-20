#!/bin/bash
set -euo pipefail

# Post Create Command hook for the local-llm-benchmark devcontainer.
# Runs inside the freshly-built Docker container before VS Code launches.

# Install the package with its core dependencies (duckdb, pyarrow, rich)
# and the `local-llm-benchmark` console-script entry point.
pip install -e ".[dev, transformers]" --target ./local_llm_benchmark

# Optional LLM engine backends (commented — uncomment to install).
# Each extras group is defined in pyproject.toml [project.optional-dependencies].
#   vllm      -> httpx>=0.27
#   ollama    -> httpx>=0.27
#   llama-cpp -> httpx>=0.27
#   transformers -> transformers>=4.40, torch>=2.2
#
#   pip install -e ".[vllm]"
#   pip install -e ".[ollama]"
#   pip install -e ".[llama-cpp]"
#   pip install -e ".[transformers]"

# Install frontend dependencies using npm.
# This installs Astro and testing libraries for frontend testing.
npm install --prefix ./local_llm_benchmark-ui

# Verify the CLI is functional.
# local-llm-benchmark --help
