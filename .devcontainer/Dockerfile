# Base image: recent Node.js 20 LTS. The migrated tool is browser-only: all
# logic runs in the browser and is managed with pnpm (Vite + SvelteKit +
# TypeScript).
FROM mcr.microsoft.com/devcontainers/javascript-node:26-trixie

# Ensure the non-root `vscode` user (created by the base image) can read and
# write the workspace, and enable shell history.
COPY --chown=vscode:vscode . /workspace

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONWARNINGS=ignore

# The tool no longer ships a Python backend; the CLI/runner and package are
# removed. Only Node tooling remains. pnpm is installed as the package
# manager (per the ADR decisions); corepack is bundled for parity work.
RUN apt-get update \
    && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm@9 corepack@latest

CMD ["pnpm", "run", "dev"]
