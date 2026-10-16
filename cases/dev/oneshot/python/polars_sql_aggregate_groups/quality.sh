#!/usr/bin/env bash
set -euo pipefail

export RUSTUP_TOOLCHAIN=nightly-2026-09-01
export CARGO_BUILD_JOBS=2
export VIRTUAL_ENV=/opt/venv

cargo check --manifest-path py-polars/runtime/polars-runtime-32/Cargo.toml --locked --offline
python -m compileall -q py-polars/src/polars
