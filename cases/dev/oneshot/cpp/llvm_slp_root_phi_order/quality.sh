#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target opt -j"$(nproc)"
