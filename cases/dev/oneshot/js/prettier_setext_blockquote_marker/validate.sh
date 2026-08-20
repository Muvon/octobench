#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/prettier/prettier"
GOLD_SHA="07184252aa4a84fcc542f34e5e70291a08b5de3a"
TEST_PATHS=(
  tests/format/markdown/heading/setext/blockquote.md
  tests/format/markdown/heading/setext/__snapshots__/format.test.js.snap
)

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"
# Drop untracked fixtures the agent may have left: the runner globs the whole
# directory, so a stray repro file would be collected as a test.
git -c safe.directory='*' clean -fq tests/format/markdown/heading/setext || true

# Whole markdown heading suite: the new blockquote fixture plus the existing
# setext and ATX snapshots, so a fix that strips markers too eagerly also fails.
# --forceExit: jest leaves open handles here and never returns once the suite
# has reported, which stalls validation indefinitely rather than failing it.
yarn jest tests/format/markdown/heading --ci --forceExit --maxWorkers=2
