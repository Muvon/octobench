#!/usr/bin/env bash
set -euo pipefail
cargo check -p rayon --tests -q
