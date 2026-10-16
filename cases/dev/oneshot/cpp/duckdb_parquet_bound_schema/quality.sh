#!/usr/bin/env bash
set -euo pipefail
cmake --build build/debug --target unittest -j"$(nproc)"
