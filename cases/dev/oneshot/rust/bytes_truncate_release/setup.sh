#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tokio-rs/bytes"
BASE_SHA="002df10b8c610788b2730ec1234934e81aaa2880"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test --test test_bytes --no-run -q
