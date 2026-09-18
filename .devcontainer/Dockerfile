# Base image: recent Python 3.11 (satisfies requires-python = ">=3.10")
FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS using NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Ensure the non-root `vscode` user (created by the base image) can read
# the workspace and write to it, and enable shell history.
COPY --chown=vscode:vscode . /workspace

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    Mypy_path=src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONWARNINGS=ignore

# Use bash as the default shell.
CMD /bin/bash
