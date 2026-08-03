#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pytest-dev/pytest"
BASE_SHA="85003621822f9c10063940068ccacc9c12b8c73f"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

pip install -q -e .
