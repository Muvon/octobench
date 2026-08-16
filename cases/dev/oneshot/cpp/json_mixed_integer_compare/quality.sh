#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target test-comparison_cpp20 -j"$(nproc)"
