#!/usr/bin/env bash
set -euo pipefail
cmake --build build --target printf-test -j"$(nproc)"
