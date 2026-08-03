#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/BurntSushi/ripgrep"
GOLD_SHA="435f59fc4b43af3ab32f34d53fa34978f393fe52"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"

# Held-out tests live INSIDE crates/ignore/src/walk.rs (#[cfg(test)] mod).
# Graft gold's test module onto the agent's file so the fix survives. The gold
# module also carries ripgrep's pre-existing walk tests, so one run covers
# fail-to-pass AND the "everything else still works" regressions.
# The graft is TEMPORARY: the pristine file is restored afterwards so the
# workspace is left unmutated (verify_case.sh applies the gold source diff
# after the base leg — a persisted graft breaks its patch context).
cp crates/ignore/src/walk.rs /tmp/_pristine_walk.rs
restore() { cp /tmp/_pristine_walk.rs crates/ignore/src/walk.rs; }
trap restore EXIT

git show "${GOLD_SHA}:crates/ignore/src/walk.rs" > /tmp/_gold_walk.rs
awk '/^#\[cfg\(test\)\]$/{exit} {print}' crates/ignore/src/walk.rs > /tmp/_agent_head.rs
awk 'f{print} /^#\[cfg\(test\)\]$/{if(!f){f=1; print}}' /tmp/_gold_walk.rs > /tmp/_gold_tests.rs
cat /tmp/_agent_head.rs /tmp/_gold_tests.rs > crates/ignore/src/walk.rs

cargo test -p ignore --lib walk::tests
