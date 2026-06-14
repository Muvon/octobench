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

echo "[setup] locating minimax provider file"
if [[ -f "src/llm/providers/minimax.rs" ]]; then
  MINIMAX_FILE="src/llm/providers/minimax.rs"
else
  MATCH_COUNT="$(rg --files | rg '/minimax\.rs$' | wc -l | tr -d ' ')"
  if [[ "${MATCH_COUNT}" != "1" ]]; then
    echo "expected exactly one minimax.rs fallback match, found ${MATCH_COUNT}"
    exit 1
  fi
  MINIMAX_FILE="$(rg --files | rg '/minimax\.rs$' | head -n 1)"
fi

# Corrupt delimiters in a less-trivial way:
# 1) duplicate a short closing-brace tail block near the middle
# 2) remove one opening brace from a nearby earlier line
TOTAL_LINES="$(wc -l < "${MINIMAX_FILE}" | tr -d ' ')"
HALF_LINE="$((TOTAL_LINES / 2))"
TARGET_LINE="$(awk -v start="${HALF_LINE}" 'NR >= start && $0 ~ /^[[:space:]]*}[[:space:]]*$/ { print NR; exit }' "${MINIMAX_FILE}")"

if [[ -z "${TARGET_LINE}" ]]; then
  TARGET_LINE="$(awk '$0 ~ /^[[:space:]]*}[[:space:]]*$/ { print NR; exit }' "${MINIMAX_FILE}")"
fi

if [[ -z "${TARGET_LINE}" ]]; then
  echo "No standalone closing brace found in ${MINIMAX_FILE}"
  exit 1
fi

BLOCK_START="$((TARGET_LINE - 2))"
if (( BLOCK_START < 1 )); then
  BLOCK_START=1
fi

echo "[setup] corrupting ${MINIMAX_FILE} by duplicating a closing-brace tail block near mid-file"
awk -v target="${TARGET_LINE}" -v block_start="${BLOCK_START}" '
  { lines[NR] = $0 }
  END {
    for (i = 1; i <= NR; i++) {
      print lines[i]
      if (i == target) {
        for (j = block_start; j <= target; j++) {
          print lines[j]
        }
      }
    }
  }
' "${MINIMAX_FILE}" > "${MINIMAX_FILE}.tmp"
mv "${MINIMAX_FILE}.tmp" "${MINIMAX_FILE}"

OPEN_SEARCH_START="$((HALF_LINE / 2))"
if (( OPEN_SEARCH_START < 1 )); then
  OPEN_SEARCH_START=1
fi
OPEN_LINE="$(awk -v start="${OPEN_SEARCH_START}" -v end="${TARGET_LINE}" '
  NR >= start && NR <= end && $0 ~ /\{/ { line = NR }
  END { if (line) print line }
' "${MINIMAX_FILE}")"

if [[ -n "${OPEN_LINE}" ]]; then
  echo "[setup] removing one opening brace near mid-file (line ${OPEN_LINE})"
  awk -v line="${OPEN_LINE}" '
    NR == line { sub(/\{/, "") }
    { print }
  ' "${MINIMAX_FILE}" > "${MINIMAX_FILE}.tmp"
  mv "${MINIMAX_FILE}.tmp" "${MINIMAX_FILE}"
else
  echo "[setup] warning: could not find an opening brace line to remove"
fi

echo "[setup] removing .git metadata to prevent reset/checkout shortcuts"
rm -rf .git

echo "[setup] removing INSTRUCTIONS.md to avoid octomind advantage"
rm -rf INSTRUCTIONS.md

echo "Prepared broken file: ${MINIMAX_FILE} (duplicated brace-tail block ending at line ${TARGET_LINE}; removed one { line=${OPEN_LINE:-n/a})"
