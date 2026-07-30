#!/usr/bin/env bash
# Reverse task collection: reconstruct the originating task from a real merged
# commit using the tap agent developer:reverse-spec (octomind).
#
# Usage: scripts/reverse_spec.sh <repo_url> <gold_sha> [out_file]
#
# Fetches the commit (depth 2, so HEAD and its parent exist for `git show`),
# checks it out in a throwaway dir, and runs the reverse-spec agent on HEAD.
# Output (Task Prompt + Clarified Spec + Evidence) goes to stdout or out_file.
# Model override via OCTOBENCH_REVERSE_MODEL (default ollama:glm-5.2).
set -euo pipefail

REPO_URL="${1:?usage: reverse_spec.sh <repo_url> <gold_sha> [out_file]}"
GOLD_SHA="${2:?missing gold sha}"
OUT_FILE="${3:-}"
MODEL="${OCTOBENCH_REVERSE_MODEL:-ollama:glm-5.2}"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/reverse-spec.XXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

git -C "${WORK}" init -q .
git -C "${WORK}" remote add origin "${REPO_URL}"
git -C "${WORK}" fetch -q --depth 2 origin "${GOLD_SHA}"
git -C "${WORK}" checkout -q "${GOLD_SHA}"

PROMPT="Reverse-spec the last commit (HEAD, ${GOLD_SHA}). Output the full reverse spec."

if [[ -n "${OUT_FILE}" ]]; then
  (cd "${WORK}" && echo "${PROMPT}" \
    | octomind run developer:reverse-spec -m "${MODEL}" --format=plain) \
    | sed -e 's/\x1b\[[0-9;]*m//g' -e 's/\x1b\[[0-9;]*[A-Za-z]//g' > "${OUT_FILE}"
  echo "wrote ${OUT_FILE}" >&2
else
  (cd "${WORK}" && echo "${PROMPT}" \
    | octomind run developer:reverse-spec -m "${MODEL}" --format=plain)
fi
