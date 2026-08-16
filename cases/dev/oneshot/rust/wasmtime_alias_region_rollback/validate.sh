#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/bytecodealliance/wasmtime"
GOLD_SHA="b17fa0c15eff5a43cf029c5926182c709d6efa94"
TEST_PATHS=(
  cranelift/filetests/filetests/alias/issue-14131-atomic.clif
  cranelift/filetests/filetests/alias/issue-14131.clif
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo run -q -p cranelift-tools -- test "${TEST_PATHS[@]}"
