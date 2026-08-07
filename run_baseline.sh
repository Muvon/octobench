#!/usr/bin/env bash
# Baseline lock — hand-picked cases from cases/dev (currently 18 oneshot + 2 longrun).
# The list below IS the baseline definition; nothing is copied or linked on disk.
#
# Fixed configuration:
#   agent          HEAD binary via HEAD_BIN (NOT the image's baked octomind)
#   agent model    ollama:glm-5.2          (configs/run-matrix.cases-octomind.yaml)
#   compression    ollama:kimi-k2.7-code
#   supervisor     ollama:qwen3.5:397b
#   gate + judge   ollama:minimax-m3
#   websearch      DENIED (cli.main install_guardrails)
#
# Results are NOT comparable to any run where websearch was available.
set -o pipefail   # NOT -u: eval of ~/.zshrc references $PS1, unset non-interactively
cd "$(dirname "$0")"

HEAD_BIN=${HEAD_BIN:?set HEAD_BIN to the octomind binary under test}
OUT=${OUT:-results-baseline}
CFG=${CFG:-configs/run-matrix.cases-octomind.yaml}
IMG=${IMG:-octobench-agent:latest}

ONESHOT=(
  cases/dev/oneshot/cpp/redis_acl_effective_keys
  cases/dev/oneshot/cpp/fmt_printf_oob_read
  cases/dev/oneshot/cpp/spdlog_srcloc_lifetime
  cases/dev/oneshot/cpp/simdjson_bigint_boundary
  cases/dev/oneshot/js/react_hidden_hydration_hang
  cases/dev/oneshot/js/fastify_query_method
  cases/dev/oneshot/js/eslint_unreachable_loop_crash
  cases/dev/oneshot/js/hono_csp_dual_policy
  cases/dev/oneshot/php/guzzle_cookie_prefixes
  cases/dev/oneshot/php/flysystem_mimetype_null
  cases/dev/oneshot/php/dbal_sqlite_alter_preserves_constraints
  cases/dev/oneshot/python/anyio_cancel_spin
  cases/dev/oneshot/python/fastapi_sse_line_splitting
  cases/dev/oneshot/python/werkzeug_float_url_notation
  cases/dev/oneshot/python/pydantic_pipeline_constraints
  cases/dev/oneshot/rust/rustls_misplaced_extensions
  cases/dev/oneshot/rust/uuid_parse_panic
  cases/dev/oneshot/rust/tokio_alt_timer_cancel_race
)
LONGRUN=(
  cases/dev/longrun/cpp/cli11
  cases/dev/longrun/python/aiohttp
)

eval "$(grep '^export ' ~/.zshrc 2>/dev/null)" 2>/dev/null
export OCTOBENCH_JUDGE_MODEL=${OCTOBENCH_JUDGE_MODEL:-ollama:minimax-m3}
export OCTOMIND_BIN="$HEAD_BIN"

for p in "${ONESHOT[@]}" "${LONGRUN[@]}"; do
  [ -d "$p" ] || { echo "MISSING CASE: $p"; exit 1; }
done

echo "[$(date +%H:%M:%S)] baseline | $("$HEAD_BIN" --version) | out=$OUT"

for p in "${ONESHOT[@]}"; do
  echo "[$(date +%H:%M:%S)] --- oneshot: $p"
  .venv/bin/python -m cli.main run \
    --cases "$p" --config "$CFG" \
    --executor docker --image "$IMG" \
    --out "$OUT" --verbosity normal
done

for p in "${LONGRUN[@]}"; do
  echo "[$(date +%H:%M:%S)] --- longrun: $p"
  .venv/bin/python -m cli.longrun run \
    --sequence "$p" --config "$CFG" \
    --executor docker --image "$IMG" \
    --out "$OUT-longrun" --verbosity normal
done

echo "[$(date +%H:%M:%S)] ALL DONE"
