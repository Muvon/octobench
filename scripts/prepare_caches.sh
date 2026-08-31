#!/usr/bin/env bash
# Prepare the shared caches every benchmark container mounts. Idempotent: run it
# once per machine, and again after an image or tap change.
#
# Why this exists: agents fetch a tap (github) and embedding models (huggingface,
# 1.3G total) on first use. Neither host is on the egress allowlist, so inside a
# sealed container those fetches FAIL — silently degrading the run — and outside
# one they are pure measured overhead (32s before the first model request).
# Warming them here means every run starts from the same prepared state.
#
#   scripts/prepare_caches.sh [image]
set -eo pipefail
IMAGE="${1:-octobench-agent:latest}"
ROOT="${OCTOBENCH_CACHE_ROOT:-$HOME/.cache/octobench}"
TAP="$ROOT/tap"
MODELS="$ROOT/models"
mkdir -p "$MODELS/huggingface" "$MODELS/octolib"

echo "cache root: $ROOT"

# --- tap: octomind's agent manifests ---------------------------------------
if [ -d "$TAP/.git" ]; then
  echo "tap: updating $TAP"
  git -C "$TAP" pull --quiet --ff-only || echo "tap: pull failed, keeping staged copy"
else
  echo "tap: cloning into $TAP"
  rm -rf "$TAP"
  git clone --depth 1 --quiet https://github.com/muvon/octomind-tap "$TAP"
fi

# --- models: warm by running the agent once, unsealed ------------------------
# A trivial prompt is enough: the embedding models load at session start, before
# any work. Caches are bind-mounted rw so what it downloads lands on the host.
if [ -s "$MODELS/huggingface/.warmed" ] && [ -s "$MODELS/octolib/.warmed" ]; then
  echo "models: already warmed ($(du -sh "$MODELS" | cut -f1))"
else
  echo "models: warming (downloads ~1.3G on first run)"
  docker rm -f octobench-cache-warm >/dev/null 2>&1 || true
  docker run --rm --name octobench-cache-warm -w /workspace \
    -e OPENAI_API_KEY -e OLLAMA_API_KEY -e OPENROUTER_API_KEY -e ANTHROPIC_API_KEY \
    -e OCTOMIND_CONFIG_PATH=/cfg/octomind.toml \
    -v "$PWD/configs/octomind/octomind.toml:/cfg/octomind.toml:ro" \
    -v "$TAP:/root/.local/share/octomind/taps/muvon/octomind-tap:ro" \
    -v "$MODELS/huggingface:/root/.cache/huggingface" \
    -v "$MODELS/octolib:/root/.cache/octolib" \
    ${OCTOMIND_BIN:+-v "$OCTOMIND_BIN:/usr/local/bin/octomind:ro"} \
    "$IMAGE" bash -lc 'echo "Reply with the single word OK and finish." | \
       octomind run developer --name cache-warm-$$ --model "${OCTOBENCH_WARM_MODEL:-openai:gpt-5.6-luna}" \
       --format=jsonl 2>&1 | tail -2'
  date -u +%FT%TZ > "$MODELS/huggingface/.warmed"
  date -u +%FT%TZ > "$MODELS/octolib/.warmed"
fi

echo
echo "prepared:"
du -sh "$TAP" "$MODELS/huggingface" "$MODELS/octolib" 2>/dev/null
echo "containers mount these automatically (runners/executor.py DEFAULT_CACHE_ROOT)."
