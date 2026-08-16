#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rust-lang/cargo"
BASE_SHA="97b3bcefc74ddf1203b21f158129e4b7df33254a"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test --test testsuite --no-run
