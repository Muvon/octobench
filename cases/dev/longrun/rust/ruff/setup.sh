#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/astral-sh/ruff"
BASE_SHA="f3c869da1b4962ff17d3f1674fb887e0d065a7df"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# rust-toolchain.toml pins 1.97.1 exactly; tests must run offline. Install the
# pinned toolchain now (network allowed) or fall back to the system toolchain.
if command -v rustup >/dev/null 2>&1; then
  rustup toolchain install 1.97.1 --profile minimal -q 2>/dev/null || rm -f rust-toolchain.toml
else
  rm -f rust-toolchain.toml
fi

# Heavy warm build: salsa, parser/AST, ruff_db, ty_vendored (packs the in-tree
# typeshed at build time, offline), ty_test. Default features.
cargo fetch -q 2>/dev/null || true
cargo test -q -p ty_python_semantic --test mdtest --no-run 2>/dev/null || true
