#!/usr/bin/env bash
set -euo pipefail

GOLD_SHA="4bace2fc28191d28dc2d1b54573923853768b86c"
TEST_PATH="modules/geometry/test/test_boundingrect.cpp"

git remote add origin https://github.com/opencv/opencv 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATH}"
cmake --build build --target opencv_test_geometry -j"$(nproc)"
build/bin/opencv_test_geometry --gtest_filter=Imgproc_BoundingRect.bool_mask_29578
