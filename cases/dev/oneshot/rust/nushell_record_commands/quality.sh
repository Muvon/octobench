#!/usr/bin/env bash
set -euo pipefail
cargo check --locked --offline -p nu-command
