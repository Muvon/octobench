#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tokio-rs/tokio"
BASE_SHA="a46338401b9e0ffc9bd68c31100ee99cee717481"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B master
git remote remove origin

RUSTFLAGS="--cfg tokio_unstable" cargo test -p tokio --lib --features full --no-run
RUSTFLAGS="--cfg loom --cfg tokio_unstable" cargo test -p tokio --lib --features full --no-run
