#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/image-rs/image"
GOLD_SHA="3f2b621ebc8a35bd098eaf18e2dc840883cdd9af"
TEST_PATHS=(tests/reference/ico/images/bmp-24bpp-mask.ico.png)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

cargo test --test reference_images
