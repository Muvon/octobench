#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/bytecodealliance/wasmtime"
BASE_SHA="720a547aa18e4661f47fdbd182e13b40db49fb30"

git config --global --add safe.directory "$(pwd)"
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
# The wast harness reads the spec/component-model testsuites from submodules.
git submodule update -q --init --depth 1
git remote remove origin

# The wast test binary depends on test-programs, which compiles wasm guest artifacts.
rustup target add wasm32-wasip1 wasm32-unknown-unknown

cargo test --locked -p wasmtime-cli --test wast --no-run
