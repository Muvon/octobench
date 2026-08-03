#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/uuid-rs/uuid"
GOLD_SHA="2320c6a0335cfddaec4df58d1a7fe410070ab9e9"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"

# The held-out tests live INSIDE src/parser.rs (#[cfg(test)] mod). A wholesale
# checkout would revert any agent fix written in that file (its non-test code is
# base-identical to gold), so graft gold's test module onto the agent's file:
# agent code up to the first top-level #[cfg(test)], gold from there on.
git show "${GOLD_SHA}:src/parser.rs" > /tmp/_gold_parser.rs
awk '/^#\[cfg\(test\)\]$/{exit} {print}' src/parser.rs > /tmp/_agent_head.rs
awk 'f{print} /^#\[cfg\(test\)\]$/{if(!f){f=1; print}}' /tmp/_gold_parser.rs > /tmp/_gold_tests.rs
cat /tmp/_agent_head.rs /tmp/_gold_tests.rs > src/parser.rs

cargo test --lib
