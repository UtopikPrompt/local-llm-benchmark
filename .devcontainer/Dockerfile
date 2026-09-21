# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# local-llm-benchmark devcontainer image
#   * Exact Python 3.12.x CLI core (project requires >=3.10) — installed via
#     python-build-standalone (prebuilt CPython 3.12.x, not the Debian 3.11)
#   * Node.js 20.x LTS for the Astro (buildless JS/TS) web UI (Astro requires >=18.17.0)
#
# The Python CLI and the Astro UI use SEPARATE toolchains. The CLI is pure
# Python (stdlib + PyPI deps); the Astro UI has its own Node/npm dependency
# tree and is NOT installed for the CLI to run. Both run inside this image.
# ---------------------------------------------------------------------------

FROM mcr.microsoft.com/devcontainers/python:3.12

# ---- System base deps ----------------------------------------------------
# Minimal runtime deps for the app + tools needed by the install scripts below.
# (Python is installed separately via build-standalone, not apt.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS using NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs
    
COPY . /workspace

CMD /bin/bash
