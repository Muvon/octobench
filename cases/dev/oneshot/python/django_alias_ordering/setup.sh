#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/django/django"
BASE_SHA="3436cf9bce84bb1f6877ad96819637366b27b719"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

python -m pip install -q uv
uv python install 3.12
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -q -e .
