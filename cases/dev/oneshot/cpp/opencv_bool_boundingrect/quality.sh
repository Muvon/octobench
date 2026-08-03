#!/usr/bin/env bash
set -euo pipefail

cmake --build build --target opencv_test_geometry -j"$(nproc)"
