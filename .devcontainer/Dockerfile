FROM mcr.microsoft.com/devcontainers/python:3.14

# Silence corepack's interactive npm download prompt so a non-interactive
# `pnpm install` in the dev container's postCreateCommand cannot hang.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# ---- Node.js 22 + tooling (installed inside the container only) ----
RUN apt-get update \
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
