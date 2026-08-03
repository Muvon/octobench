#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fastapi/fastapi"
BASE_SHA="31ce3cb8d73a6e20221315a90dd98a117f0101a0"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

pip install -q -e .
pip install -q pytest httpx2 fastar pytest-timeout
