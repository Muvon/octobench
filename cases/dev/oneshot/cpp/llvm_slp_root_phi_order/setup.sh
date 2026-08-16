#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/llvm/llvm-project"
BASE_SHA="227ec3e87fd013ad1963827144ff8f6e9d762510"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

cmake -S llvm -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_TARGETS_TO_BUILD=X86 \
  -DLLVM_INCLUDE_TESTS=ON \
  -DLLVM_ENABLE_ASSERTIONS=ON > /dev/null
cmake --build build --target opt FileCheck -j"$(nproc)" > /dev/null
