#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/python/mypy"
BASE_SHA="0007c5267287ba47a3e4acc022ecb149fcf702e2"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# typeshed is vendored in-tree; no submodules. Plain (non-mypyc) install.
pip install -q -r test-requirements.txt
pip install -q -e .
