#!/usr/bin/env bash
set -euo pipefail
cmake --build build -j"$(nproc)" --target spdlog-utests
