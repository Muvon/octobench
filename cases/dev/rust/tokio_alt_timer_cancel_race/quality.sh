#!/usr/bin/env bash
set -euo pipefail

RUSTFLAGS="--cfg loom --cfg tokio_unstable" cargo check -p tokio --features full
