#!/usr/bin/env bash
# Serve host mirrors on the Docker bridge; verify Git transport from a container.
set -euo pipefail

ACTION=${1:?usage: git_mirror_daemon.sh <start|status> [image]}
IMAGE=${2:-octobench-agent:latest}
PROBE_TIMEOUT=20
case "$ACTION" in
  start|status) ;;
  *) echo "FATAL: expected start or status, got $ACTION" >&2; exit 2 ;;
esac
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MIRRORS=${OCTOBENCH_GIT_MIRRORS-$HOME/.cache/octobench/git-mirrors}
[ -n "$MIRRORS" ] && [ -d "$MIRRORS" ] || {
  echo "FATAL: OCTOBENCH_GIT_MIRRORS is not a mirror directory: $MIRRORS" >&2; exit 2;
}
MIRRORS=$(cd "$MIRRORS" && pwd -P)
PROBE_URL=$(python3 - "$REPO" "$MIRRORS" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from runners.executor import git_mirror_urls

print(next(iter(git_mirror_urls(Path(sys.argv[2])).values())))
PY
)
GATEWAY=${PROBE_URL#git://}
GATEWAY=${GATEWAY%%:*}

# Concurrent campaign launchers must not start competing daemons.
exec 9>"$MIRRORS/.daemon.lock"
flock -x 9
if ! timeout "$PROBE_TIMEOUT" git ls-remote "$PROBE_URL" >/dev/null 2>&1; then
  if [ "$ACTION" = status ]; then
    echo "FATAL: git mirror daemon is not serving $PROBE_URL" >&2; exit 1
  fi
  # The host git ships without `git daemon` and needs no root this way: serve the
  # mirrors read-only from a tiny container published on the bridge gateway.
  DAEMON_IMAGE=octobench-git-daemon:1
  DAEMON_NAME=octobench-git-daemon
  if ! docker image inspect "$DAEMON_IMAGE" >/dev/null 2>&1; then
    docker build -q -t "$DAEMON_IMAGE" - >/dev/null <<'DOCKERFILE'
FROM alpine:3.20
RUN apk add --no-cache git git-daemon
DOCKERFILE
  fi
  docker rm -f "$DAEMON_NAME" >/dev/null 2>&1 || true
  docker run -d --name "$DAEMON_NAME" --restart unless-stopped \
    -p "$GATEWAY:9418:9418" -v "$MIRRORS:/srv/git:ro" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
    "$DAEMON_IMAGE" git daemon --export-all --base-path=/srv/git --reuseaddr --port=9418 \
    --enable=upload-pack --forbid-override=upload-pack \
    --disable=receive-pack --forbid-override=receive-pack \
    --disable=upload-archive --forbid-override=upload-archive /srv/git >/dev/null 9>&-
  for _ in $(seq 1 20); do
    timeout 5 git ls-remote "$PROBE_URL" >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! docker run --rm --network bridge --entrypoint timeout "$IMAGE" \
  "$PROBE_TIMEOUT" git ls-remote "$PROBE_URL" >/dev/null; then
  echo "FATAL: configured git mirrors are unreachable from a container: $PROBE_URL" >&2
  exit 1
fi
echo "GIT-MIRROR-READY $PROBE_URL (verified from $IMAGE)"
