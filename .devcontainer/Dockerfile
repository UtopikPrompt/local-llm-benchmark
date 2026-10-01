FROM mcr.microsoft.com/devcontainers/python:1.3-3.12

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
