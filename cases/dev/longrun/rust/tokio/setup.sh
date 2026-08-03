#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tokio-rs/tokio"
BASE_SHA="fe258f5e6d39a604b67d3cf54559d5918a3f353a"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo build --tests 2>/dev/null || true
