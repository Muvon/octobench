#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/clap-rs/clap"
BASE_SHA="70752392a8ca7ea877c651622a2247b2ccc0fb5e"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

# Warm the build cache for the test targets the turns use.
cargo build -p clap --features "deprecated derive cargo env unicode string wrap_help unstable-ext" --tests 2>/dev/null || true
cargo build -p clap_complete -p clap_complete_nushell --tests 2>/dev/null || true
