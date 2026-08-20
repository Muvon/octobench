#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/hyperium/hyper"
GOLD_SHA="3534d75c898da17b023e6bff9b4cf71afed123ad"
TARGET="src/proto/h1/role.rs"

git remote add origin "${REPO_URL}" 2>/dev/null || true
git fetch -q --depth 1 origin "${GOLD_SHA}"

# The held-out tests live INSIDE src/proto/h1/role.rs (#[cfg(test)] mod). A
# wholesale checkout would revert the agent's fix, which lives in the same file,
# so graft gold's test module on: agent code up to the first top-level
# #[cfg(test)], gold from there on. The pristine file is restored afterwards so
# the workspace is left unmutated for the evidence diff.
cp "${TARGET}" /tmp/_pristine_role.rs
restore() { cp /tmp/_pristine_role.rs "${TARGET}"; }
trap restore EXIT

git show "${GOLD_SHA}:${TARGET}" > /tmp/_gold_role.rs
awk '/^#\[cfg\(test\)\]$/{exit} {print}' "${TARGET}" > /tmp/_agent_head.rs
awk 'f{print} /^#\[cfg\(test\)\]$/{if(!f){f=1; print}}' /tmp/_gold_role.rs > /tmp/_gold_tests.rs
cat /tmp/_agent_head.rs /tmp/_gold_tests.rs > "${TARGET}"

cargo test --features full --lib proto::h1::role
