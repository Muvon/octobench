#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/bytecodealliance/wasmtime"
BASE_SHA="eba60a7257cf24f03bc8d2246bca7edff170ba2d"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cargo build -q -p cranelift-tools
