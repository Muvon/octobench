#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rust-lang/cargo"
BASE_SHA="88e0ae88276c937e4a5614c8b2812fa9902193a3"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

cargo test --test testsuite --no-run
