#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target benchmark -j"$(nproc)"
