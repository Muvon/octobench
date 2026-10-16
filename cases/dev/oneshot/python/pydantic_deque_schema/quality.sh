#!/usr/bin/env bash
set -euo pipefail
cargo check --locked --offline --manifest-path pydantic-core/Cargo.toml
python -m compileall -q pydantic/ pydantic-core/python/pydantic_core/
