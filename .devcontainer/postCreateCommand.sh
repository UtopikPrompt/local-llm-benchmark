#!/usr/bin/env bash
# Runs inside the non-root `vscode` user created by the devcontainer base image.
set -euo pipefail

# Disable corepack's interactive download prompt so `pnpm install` runs
# non-interactively during devcontainer startup.
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# Install dependencies with pnpm.
pnpm install

# Start the Vite dev server in the background so HMR is ready when the
# container opens.
pnpm run dev -- --host &
