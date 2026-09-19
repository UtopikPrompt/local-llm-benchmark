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

FROM debian:bookworm-slim AS base

# ---- System base deps ----------------------------------------------------
# Minimal runtime deps for the app + tools needed by the install scripts below.
# (Python is installed separately via build-standalone, not apt.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# ---- Exact Python 3.12.x (build-standalone) -------------------------------
# The Debian bookworm-slim `python3` package is Python 3.11, which does NOT
# provide the exact version the image requires. We install an exact, prebuilt
# CPython 3.12.x from the official python-build-standalone artifact: a single
# self-contained build that installs to /usr/local without compiling (keeping
# the image lean) and guarantees the exact 3.12 patch version. `--pip --venv`
# provide system pip and `python3 -m venv`.
RUN curl -fsSL https://github.com/indygreg/python-build-standalone/releases/latest/download/install-python3.12.sh -o /tmp/install-python3.12.sh && \
    bash /tmp/install-python3.12.sh 3.12 --prefix=/usr/local --pip --venv && \
    rm /tmp/install-python3.12.sh && \
    python3 --version

# ---- Node.js 20.x LTS (Astro web UI) --------------------------------------
# NodeSource provides the Node.js 20.x LTS release (satisfies Astro's >=18.17.0).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        ca-certificates \
    && \
    curl -fsS https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh && \
    bash /tmp/nodesource_setup.sh && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /tmp/nodesource_setup.sh && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy the repo. The Astro UI's own npm install happens later (after node/npm
# are present) so the image stays lean and the CLI deps are not duplicated.
COPY . .

# Activate the virtualenv and install the Python CLI core (editable) plus the
# `transformers` engine extra as a sensible default engine, then install the
# Astro web UI's npm dependencies.
RUN python3 -m venv .venv && \
    . .venv/bin/activate && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ".[transformers]"

# Install the Astro (buildless JS/TS) web UI dependencies via npm. Astro's
# toolchain is separate from the Python CLI and runs only for the UI.
# The Astro project lives in ./ui; adjust if your layout differs.
RUN npm install --prefix ./ui

# ---- Non-root user ---------------------------------------------------------
# Set a non-root user. The home directory is writable so the user can write
# runtime artifacts that .gitignore ignores: `.venv/`, `benchmark-results/`,
# and `astro/dist/`. Using the ${localProcessUid}/${localProcessGid} values
# (set in devcontainer.json) keeps the built image's ownership aligned with the
# host checkout, avoiding "permission denied" when VS Code Remote syncs files.
RUN groupadd --gid 56789 vscode && \
    useradd --uid 56789 --gid vscode --home-dir /workspace --create-home --shell /bin/bash vscode && \
    chown -R vscode:vscode /workspace

USER vscode

CMD ["tail", "-f", "/dev/null"]
