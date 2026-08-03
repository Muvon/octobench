#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/aio-libs/aiohttp"
BASE_SHA="04f3a5fa2a786f26b30426a69c7a97d9d47c9e75"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
# setup.py refuses to install from a git clone without the llhttp submodule,
# even with AIOHTTP_NO_EXTENSIONS=1 — init it BEFORE removing origin.
git submodule update --init --depth 1
git remote remove origin

# Pure-Python install; none of the turns touch C code.
AIOHTTP_NO_EXTENSIONS=1 pip install -q -e .
# setup.cfg [tool:pytest]: asyncio_mode=auto (pytest-aiohttp), timeout=120
# (pytest-timeout), and a filterwarnings entry importing coverage.exceptions —
# without the coverage package pytest dies at startup with PytestConfigWarning.
# Do NOT install blockbuster (optional blocking detector).
pip install -q pytest pytest-aiohttp pytest-mock pytest-timeout coverage
