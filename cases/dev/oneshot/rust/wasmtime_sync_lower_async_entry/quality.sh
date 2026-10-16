#!/usr/bin/env bash
set -euo pipefail

cargo test --locked --offline -p wasmtime-cli --test wast --no-run
