#!/usr/bin/env bash
# The only supported way to start a benchmark run.
#
# Every clean-bench campaign that produced unusable numbers did so because a
# hand-written launcher forgot one export. This script owns those settings so a
# launcher cannot forget them, and cli.main refuses to start if they are unset.
#
#   scripts/bench.sh oneshot <client> <model> [--suite NAME | --cases DIR] [--out DIR]
#   scripts/bench.sh longrun <client> <model> [--suite NAME | --cases DIR] [--out DIR]
#   scripts/bench.sh rerun   <client> <model> --out DIR [--rounds N]
#
# rerun retries only the infra-failed records of an existing run, in place, under
# the identical environment — a retry configured differently from the run it
# patches is how a column ends up half one thing and half another.
#
#   client  octomind | codex | opencode | claude
#   model   a key from configs/models.yaml (glm-5.3, claude-opus-5, gpt-5.6-sol, ...)
#   suite   a list file in configs/suites/ (oneshot default: oneshot-50).
#           Lines are `oneshot/<lang>/<case>` or `longrun/<lang>/<repo>`; one
#           suite can mix both kinds (gold does — see docs/GOLD.md) and the
#           launcher selects the lines matching MODE. Bare `<lang>/<case>`
#           lines mean oneshot (oneshot-50.txt format).
#
# Examples:
#   scripts/bench.sh oneshot octomind glm-5.3
#   scripts/bench.sh oneshot claude claude-opus-5 --out results-opus5-50
#
# Client binaries are taken from the image unless overridden in the environment
# (OCTOMIND_BIN / CODEX_BIN / OPENCODE_BIN / OCTOFS_BIN), which is how a run pins
# a specific release without rebuilding the image.
set -eo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"

MODE=${1:?usage: bench.sh <oneshot|longrun> <client> <model> [opts]}
CLIENT=${2:?missing client}
MODEL=${3:?missing model}
shift 3

SUITE=""
CASES=""
OUT=""
IMAGE=octobench-agent:latest
ROUNDS=2
while [ $# -gt 0 ]; do
  case "$1" in
    --suite) SUITE=$2; shift 2 ;;
    --cases) CASES=$2; shift 2 ;;
    --out)   OUT=$2;   shift 2 ;;
    --image) IMAGE=$2; shift 2 ;;
    --rounds) ROUNDS=$2; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
: "${OUT:=results-${MODEL}-${CLIENT}-$(date +%Y%m%d-%H%M%S)}"
if [ "$MODE" = rerun ] && [ ! -d "$OUT" ]; then
  echo "FATAL: rerun needs an existing --out dir; '$OUT' not found" >&2; exit 2
fi

case "$CLIENT" in
  octomind|codex|opencode|claude) ;;
  *) echo "FATAL: unknown client '$CLIENT'" >&2; exit 2 ;;
esac

# ── Credentials: presence only, never the value ─────────────────────────────
need_env() {
  [ -n "${!1}" ] || { echo "FATAL: $1 is not set" >&2; exit 2; }
}
need_env OPENROUTER_API_KEY   # judge panel
case "$CLIENT" in
  claude)   need_env ANTHROPIC_API_KEY ;;
  codex)    need_env OPENAI_API_KEY ;;
esac
# The model's own provider key is named in configs/models.yaml, not here; a wrong
# one surfaces immediately as a provider error on case 1.

# ── Clean-bench invariants (cli/main.py refuses to run without them) ────────
export OCTOBENCH_SYSTEM_PROMPT=configs/common/system_prompt.md
export OCTOBENCH_SEAL_NETWORK=1
export OCTOBENCH_CLEAN_WORKSPACE=1
export OCTOBENCH_JUDGE_MODELS="${OCTOBENCH_JUDGE_MODELS:-openrouter:thinkingmachines/inkling-small,openrouter:minimax/minimax-m3,openrouter:deepseek/deepseek-v4-flash-0731}"
# octomind: the bench role from configs/octomind/octomind.toml (core+octofs+octocode).
# Anything else resolves to the tap agent developer:general, whose capabilities
# include websearch and knowledge and whose prompt orders it to mirror the
# upstream merged PR — on a bench harvested from merged PRs that is the answer key.
if [ "$CLIENT" = octomind ]; then export OCTOMIND_AGENT=developer; fi

# Local git mirrors (scripts/build_git_mirrors.sh): containers fetch pinned
# SHAs from bare mirrors instead of github — the anonymous rate limit poisoned
# two campaigns before this existed.
if [ -d "$HOME/.cache/octobench/git-mirrors" ]; then
  export OCTOBENCH_GIT_MIRRORS="$HOME/.cache/octobench/git-mirrors"
  echo "git mirrors: $OCTOBENCH_GIT_MIRRORS"
fi
# Authenticated github fetches for HARNESS phases (runners/executor.py
# harness_git_env): lifts the anonymous rate limit for anything unmirrored.
if [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "github token: set (harness git auth)"
fi

# ── Preflight ───────────────────────────────────────────────────────────────
[ -f "$OCTOBENCH_SYSTEM_PROMPT" ] || { echo "FATAL: missing $OCTOBENCH_SYSTEM_PROMPT" >&2; exit 2; }
grep -q "^  $MODEL:" configs/models.yaml || { echo "FATAL: '$MODEL' is not in configs/models.yaml" >&2; exit 2; }
[ -d "$HOME/.cache/octobench/models" ] || echo "WARNING: no warmed model cache — run scripts/prepare_caches.sh (sealed runs cannot fetch it)" >&2
if [ "$CLIENT" = opencode ]; then
  [ -f configs/opencode/opencode.json ] || { echo "FATAL: configs/opencode/opencode.json missing (opencode would run unconfigured)" >&2; exit 2; }
  export OPENCODE_CONFIG_JSON="${OPENCODE_CONFIG_JSON:-$REPO/configs/opencode/opencode.json}"
  # opencode is the one client not baked into the agent image; without the
  # override every case dies as "opencode: not found" and records as a run.
  [ -n "$OPENCODE_BIN" ] && [ -x "$OPENCODE_BIN" ] || {
    echo "FATAL: OPENCODE_BIN must point at an executable (opencode is not in $IMAGE)" >&2; exit 2; }
fi
AVAIL=$(df --output=avail -BG . | tail -1 | tr -dc '0-9')
[ "${AVAIL:-0}" -ge 15 ] || { echo "FATAL: only ${AVAIL}G free, need >=15G" >&2; exit 2; }

# ── Rerun: retry infra failures in place, same env, then re-audit ───────────
if [ "$MODE" = rerun ]; then
  MATRIX=$(mktemp /tmp/bench-matrix-XXXXXX.yaml)
  .venv/bin/python - "$CLIENT" "$MODEL" "$MATRIX" <<'PYEOF'
import sys, yaml
client, model, out = sys.argv[1:4]
spec = yaml.safe_load(open("configs/models.yaml"))["models"][model]
pm = (spec.get("providers") or {}).get(client)
run = {"provider": client, "model": model}
if pm:
    run["provider_model"] = pm
yaml.safe_dump({"runs": [run]}, open(out, "w"))
PYEOF
  cat "$MATRIX"
  for rj in "$OUT"/*/results.json; do
    echo "=== rerun $rj (rounds=$ROUNDS) ==="
    .venv/bin/python scripts/rerun_failed.py "$rj" "$MATRIX" "$ROUNDS"
  done
  rm -f "$MATRIX"
  echo "=== tool audit ==="
  .venv/bin/python scripts/audit_tools.py "$OUT" || {
    echo "FATAL: forbidden tool use recorded — these results are NOT comparable" >&2
    exit 1
  }
  echo "=== judge panel audit ==="
  .venv/bin/python scripts/audit_judges.py "$OUT" \
    || echo "WARNING: the records above were scored by a short panel — rejudge before publishing" >&2
  echo "BENCH-DONE $OUT"
  exit 0
fi

# ── Case selection ──────────────────────────────────────────────────────────
if [ "$MODE" = longrun ] && [ -z "$CASES" ] && [ -z "$SUITE" ]; then
  echo "FATAL: longrun needs --suite <list> or --cases <sequence tree>" >&2; exit 2
fi
if [ -z "$CASES" ]; then
  : "${SUITE:=oneshot-50}"
  if [ "$MODE" = longrun ]; then MARK=sequence.yaml; else MARK=case.yaml; fi
  LIST=configs/suites/$SUITE.txt
  [ -f "$LIST" ] || { echo "FATAL: no suite list at $LIST" >&2; exit 2; }
  # Per-out and per-mode name: two campaigns (or both kinds of one mixed
  # suite) can materialize concurrently.
  CASES=.suite-$SUITE-$MODE-$(basename "$OUT")
  rm -rf "$CASES"
  WANT=0
  while read -r rel; do
    [ -n "$rel" ] || continue
    case "$rel" in
      oneshot/*|longrun/*) kind=${rel%%/*}; sub=${rel#*/} ;;
      *) kind=oneshot; sub=$rel ;;
    esac
    [ "$kind" = "$MODE" ] || continue
    src=cases/dev/$kind/$sub
    [ -d "$src" ] || { echo "FATAL: suite lists a missing case: $src" >&2; exit 2; }
    mkdir -p "$CASES/$(dirname "$sub")"
    cp -r "$src" "$CASES/$sub"
    WANT=$((WANT+1))
  done < "$LIST"
  [ "$WANT" -gt 0 ] || { echo "FATAL: suite $SUITE has no $MODE entries" >&2; exit 2; }
  GOT=$(find -L "$CASES" -name "$MARK" | wc -l)
  [ "$GOT" -eq "$WANT" ] || { echo "FATAL: suite $SUITE wanted $WANT entries, materialized $GOT" >&2; exit 2; }
fi

echo "=== $MODE | client=$CLIENT model=$MODEL cases=$CASES out=$OUT ==="
if [ -n "$OCTOMIND_BIN" ]; then echo -n "octomind binary: "; "$OCTOMIND_BIN" --version; fi
if [ -n "${OCTOBENCH_JUDGE_BIN:-}" ]; then
  [ -x "$OCTOBENCH_JUDGE_BIN" ] || {
    echo "FATAL: OCTOBENCH_JUDGE_BIN is not executable: $OCTOBENCH_JUDGE_BIN" >&2
    exit 2
  }
  echo -n "judge binary: "; "$OCTOBENCH_JUDGE_BIN" --version
fi

if [ "$MODE" = longrun ]; then
  # One sequence per process. A sequence that dies takes only itself down, the
  # campaign resumes by skipping what is already recorded, and disk is rechecked
  # between sequences — a full disk mid-campaign has killed a run before. The
  # per-sequence cap only ever fires on a genuine hang: the longest sequence
  # ever measured is rust/ruff at 203m of agent time.
  : "${SEQ_TIMEOUT:=6h}"
  mapfile -t SEQS < <(find -L "$CASES" -name sequence.yaml | sort)
  [ "${#SEQS[@]}" -gt 0 ] || { echo "FATAL: no sequence.yaml under $CASES" >&2; exit 2; }
  echo "sequences: ${#SEQS[@]} (per-sequence cap $SEQ_TIMEOUT)"
  for sf in "${SEQS[@]}"; do
    sid=$(sed -n 's/^id: *//p' "$sf" | head -1 | tr -d "\"'" )
    if [ -n "$sid" ] && grep -qs "\"sequence_id\": \"$sid\"" "$OUT"/*/results.json; then
      echo "SKIP $sid (already recorded in $OUT)"
      continue
    fi
    FREE=$(df --output=avail -BG . | tail -1 | tr -dc '0-9')
    [ "${FREE:-0}" -ge 40 ] || { echo "ABORT: only ${FREE}G free before $sid" >&2; exit 3; }
    # GitHub anonymous rate limit: when tripped, every setup.sh dies in ~0.3s
    # with "could not read Username" and the whole list burns as setup-fails
    # in seconds (2026-09-02). Pause until anonymous fetch works again.
    # With GITHUB_TOKEN set the harness fetches authenticated (no anonymous
    # limit), so probing anonymously would only false-pause the run.
    until [ -n "${GITHUB_TOKEN:-}" ] || timeout 20 git ls-remote --heads https://github.com/CLIUtils/CLI11 >/dev/null 2>&1; do
      echo "PAUSE github anonymous fetch unavailable before $sid; retry in 300s $(date -u +%FT%TZ)"
      sleep 300
    done
    echo "START $sid free=${FREE}G $(date -u +%FT%TZ)"
    rc=0
    timeout "$SEQ_TIMEOUT" .venv/bin/python -m cli.longrun run \
      --sequence "$(dirname "$sf")" \
      --providers "$CLIENT" \
      --models "$MODEL" \
      --executor docker \
      --image "$IMAGE" \
      --out "$OUT" \
      --verbosity normal || rc=$?
    echo "FINISH $sid rc=$rc $(date -u +%FT%TZ)"
  done
else
  .venv/bin/python -m cli.main run \
    --cases "$CASES" \
    --providers "$CLIENT" \
    --models "$MODEL" \
    --executor docker \
    --image "$IMAGE" \
    --out "$OUT" \
    --verbosity normal || true
fi

# ── Post-hoc proof: no client reached the web, whatever its config said ─────
echo "=== tool audit ==="
.venv/bin/python scripts/audit_tools.py "$OUT" || {
  echo "FATAL: forbidden tool use recorded — these results are NOT comparable" >&2
  exit 1
}
# Not fatal: a short panel is recoverable by re-judging the stored payload, and
# aborting here would throw away a finished campaign over a judge outage.
echo "=== judge panel audit ==="
.venv/bin/python scripts/audit_judges.py "$OUT" \
  || echo "WARNING: the records above were scored by a short panel — rejudge before publishing" >&2
echo "BENCH-DONE $OUT"
