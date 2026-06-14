#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Muvon/octolib"
COMMIT_SHA="b46e3c7d83929ec0841aeb213991b594a5cbc098"

echo "[setup] cloning ${REPO_URL} into workspace root"
git clone "${REPO_URL}" .
echo "[setup] checking out ${COMMIT_SHA}"
git checkout "${COMMIT_SHA}"

# echo "[setup] running octocode index (this can take time)"
# octocode index

MINIMAX_FILE="src/llm/providers/minimax.rs"
if [[ ! -f "${MINIMAX_FILE}" ]]; then
  echo "expected file missing: ${MINIMAX_FILE}"
  exit 1
fi

EXPECT_DIR=".bench_expectations"
mkdir -p "${EXPECT_DIR}"

echo "[setup] capturing minimax model expectations from original implementation"
grep -oE '"[^"]*[Mm]inimax[^"]*"' "${MINIMAX_FILE}" | sed 's/^"//; s/"$//' | sort -u > "${EXPECT_DIR}/minimax_models.txt" || true
if [[ ! -s "${EXPECT_DIR}/minimax_models.txt" ]]; then
  # Fallback: capture all model-like string literals from minimax provider file.
  grep -oE '"[^"]*(model|chat|text|mini|max)[^"]*"' "${MINIMAX_FILE}" | sed 's/^"//; s/"$//' | sort -u > "${EXPECT_DIR}/minimax_models.txt" || true
fi

echo "[setup] removing minimax provider file"
rm -f "${MINIMAX_FILE}"

echo "[setup] removing .git metadata to prevent reset/checkout shortcuts"
rm -rf .git

echo "[setup] removing INSTRUCTIONS.md to avoid octomind advantage"
rm -rf INSTRUCTIONS.md

echo "Prepared feature-missing state (deleted ${MINIMAX_FILE})"
