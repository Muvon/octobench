#!/usr/bin/env bash
set -euo pipefail

# Minimal, self-contained workspace (no clone/index/build) so this case is a fast
# end-to-end smoke of the whole flow: setup -> agent edit -> validate -> judge.
cat > add.py <<'PY'
def add(a, b):
    # BUG: subtraction instead of addition
    return a - b
PY

cat > test_add.py <<'PY'
from add import add

assert add(2, 3) == 5, "2 + 3 should be 5"
assert add(10, 5) == 15, "10 + 5 should be 15"
assert add(-1, 1) == 0, "-1 + 1 should be 0"
print("OK")
PY

echo "[setup] wrote buggy add.py + test_add.py"
