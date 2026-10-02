FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Silence corepack's interactive npm download prompt so a non-interactive
# `pnpm install` in the dev container's postCreateCommand cannot hang.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# ---- Node.js 22 + tooling (installed inside the container only) ----
# Some base images include a stale Yarn APT source with an expired signing key,
# which breaks apt-get update before NodeSource can install Node.js.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && rm -f /etc/apt/sources.list.d/yarn.list.save \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Enable corepack (ships pnpm/yarn with Node)
RUN corepack enable

# Default workdir
WORKDIR /home/vscode/app
