#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/llvm/llvm-project"
GOLD_SHA="1cb114a48974f45767c2c4af4bb4647cff8eaf7d"
TEST_PATH="llvm/test/Transforms/SLPVectorizer/X86/ordered-reduction-root-phi-reorder.ll"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"

cmake --build build --target opt FileCheck -j"$(nproc)" > /dev/null
build/bin/opt < "${TEST_PATH}" -passes=slp-vectorizer -S \
  -mtriple=x86_64-unknown-linux-gnu | build/bin/FileCheck "${TEST_PATH}"
