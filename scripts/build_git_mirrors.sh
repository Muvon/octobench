#!/usr/bin/env bash
# Bare mirrors served by scripts/git_mirror_daemon.sh. The executor generates
# per-repo git:// rewrites for harness execs only; no mirror is mounted in the
# container. Idempotent: existing mirrors are fetch-updated.
#
# Usage: scripts/build_git_mirrors.sh [dest]   (default ~/.cache/octobench/git-mirrors)
set -euo pipefail
DEST=${1:-$HOME/.cache/octobench/git-mirrors}
mkdir -p "$DEST"

# Every repo named in cases/dev/longrun/*/sequence.yaml and worth caching.
# Extend when new sequences land; oneshot repos can be added the same way.
repos="CLIUtils/CLI11 duckdb/duckdb eslint/eslint fastify/fastify doctrine/orm
PHPOffice/PhpSpreadsheet python/cpython python/mypy rust-lang/cargo astral-sh/ruff
nodejs/undici vitejs/vite webpack/webpack"

for r in $repos; do
  d="$DEST/$r"
  if [ -d "$d" ]; then
    echo "update $r"
    git -C "$d" fetch -q --prune origin || echo "WARN: fetch-update failed for $r (mirror kept)"
  else
    mkdir -p "$(dirname "$d")"
    ok=""
    for try in 1 2 3 4 5; do
      if git clone -q --mirror "https://github.com/$r" "$d"; then ok=1; break; fi
      echo "retry $try for $r in 120s"; rm -rf "$d"; sleep 120
    done
    [ -n "$ok" ] || { echo "FATAL: could not mirror $r" >&2; exit 1; }
  fi
  # Arbitrary pinned-SHA fetches (setup.sh, validation) need this on the "server".
  git -C "$d" config uploadpack.allowAnySHA1InWant true
  # Some scripts append .git to clone URLs; cover both spellings.
  ln -sfn "$(basename "$d")" "$d.git"
  echo "done $r"
done

echo "MIRRORS-READY $(du -sh "$DEST" | cut -f1)"
echo "Start serving: OCTOBENCH_GIT_MIRRORS='$DEST' scripts/git_mirror_daemon.sh start"
