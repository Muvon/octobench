#!/usr/bin/env bash
# Bare mirrors of the repos benchmark cases fetch, plus the container-side
# gitconfig that reroutes those fetches to file:///git-cache (mounted by the
# executor when OCTOBENCH_GIT_MIRRORS is set). Idempotent: existing mirrors
# are fetch-updated. Rewrites are PER-REPO, so an unmirrored repo still goes
# to the network instead of hitting a missing local path.
#
# Usage: scripts/build_git_mirrors.sh [dest]   (default ~/.cache/octobench/git-mirrors)
set -eo pipefail
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

CFG="$DEST/gitconfig"
{
  printf '[safe]\n\tdirectory = *\n'
  for r in $repos; do
    printf '[url "file:///git-cache/%s"]\n\tinsteadOf = https://github.com/%s\n' "$r" "$r"
  done
} > "$CFG"
echo "MIRRORS-READY $(du -sh "$DEST" | cut -f1) ($(grep -c insteadOf "$CFG") repos rewired)"
