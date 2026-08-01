#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/seanmonstar/reqwest"
BASE_SHA="fc99bd5b15c72c65f615848d7b048df94aeadcd9"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# Warm the compile cache so validate is an incremental rebuild.
cargo test --lib --no-run -q
