#!/usr/bin/env bash
# Runs inside the non-root `vscode` user created by the devcontainer base image.
set -euo pipefail

# Install the editable package with dev extras (pytest, ruff).
pip install -e ".[dev]"

# Configure the editable install to use the workspace `src` as the path so
# `PYTHONPATH=src python -m local_llm_benchmark.runner` works.
echo 'export PYTHONPATH=src:$PYTHONPATH' >> ~/.bashrc

# Verify the install and the benchmark entry point.
python -c "import local_llm_benchmark; print(local_llm_benchmark.__file__)"
python -m local_llm_benchmark.runner --help || true
