#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/seanmonstar/reqwest"
GOLD_SHA="99996a1b3db5e7e27ce58512be42c581a9a8a7cb"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"

# The held-out tests live INSIDE src/error.rs (#[cfg(test)] mod). A wholesale
# checkout would revert the agent's fix in that same file, so graft gold's test
# module on: agent code up to the first top-level #[cfg(test)], gold from there.
git show "${GOLD_SHA}:src/error.rs" > /tmp/_gold_error.rs
awk '/^#\[cfg\(test\)\]$/{exit} {print}' src/error.rs > /tmp/_agent_head.rs
awk 'f{print} /^#\[cfg\(test\)\]$/{if(!f){f=1; print}}' /tmp/_gold_error.rs > /tmp/_gold_tests.rs
cat /tmp/_agent_head.rs /tmp/_gold_tests.rs > src/error.rs

cargo test --lib error::tests
