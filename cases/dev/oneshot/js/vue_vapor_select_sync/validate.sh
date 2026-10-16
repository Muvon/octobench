#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vuejs/core"
GOLD_SHA="db5ab78a1a38db409bce31b7e3596b44878bf268"
TEST_PATHS=(
  packages/compiler-vapor/__tests__/transforms/__snapshots__/vBind.spec.ts.snap
  packages/compiler-vapor/__tests__/transforms/vBind.spec.ts
  packages/runtime-vapor/__tests__/directives/vModel.spec.ts
  packages/runtime-vapor/__tests__/dom/prop.spec.ts
  packages/runtime-vapor/__tests__/hydration/basic.spec.ts
  packages/runtime-vapor/__tests__/renderEffect.spec.ts
  packages/runtime-vapor/__tests__/vdomInterop.spec.ts
)

git fetch -q --depth 1 "${REPO_URL}" "${GOLD_SHA}"
git checkout -q "${GOLD_SHA}" -- "${TEST_PATHS[@]}"

# Restore the whole upstream test/support trees, including transitive helpers.
# No gold production change intersects these paths; see plan.md for exceptions.
gold_paths="$(git ls-tree -r --name-only "${GOLD_SHA}")"
support_paths=()
while IFS= read -r path; do
  case "${path}" in
    */__tests__/*|scripts/*|packages/runtime-test/*|package.json|*/package.json|\
    vitest*|*/vitest*|*.config.*|tsconfig*|*/tsconfig*|\
    pnpm-lock.yaml|pnpm-workspace.yaml|.npmrc|packages/global.d.ts|env.d.ts)
      support_paths+=("${path}")
      ;;
  esac
done <<<"${gold_paths}"
git checkout -q "${GOLD_SHA}" -- "${support_paths[@]}"
for test_dir in packages/*/__tests__ scripts packages/runtime-test; do
  git -c safe.directory='*' clean -fdq -- "${test_dir}"
done

run_vitest() {
  local expected_count="$1"
  local test_output
  shift
  if ! test_output="$(
    NO_COLOR=1 FORCE_COLOR=0 pnpm exec vitest run --project unit-jsdom \
      --reporter=default --passWithNoTests=false "$@" 2>&1
  )"; then
    printf '%s\n' "${test_output}"
    exit 1
  fi
  printf '%s\n' "${test_output}"
  if ! grep -Eq "^[[:space:]]*Tests[[:space:]]+${expected_count} passed([[:space:]]|$)" <<<"${test_output}"; then
    echo "expected ${expected_count} passing selected tests" >&2
    exit 1
  fi
}

run_vitest 5 packages/runtime-vapor/__tests__/directives/vModel.spec.ts \
  -t '(select model takes precedence over .* after options update|reapplies an unchanged select model after child component options update|updates selection once before hooks for owner and child input updates|disposes queued selection updates before reading a removed model)$'
run_vitest 48 packages/runtime-vapor/__tests__/dom/prop.spec.ts \
  -t 'select value with rendered options'
run_vitest 4 packages/runtime-vapor/__tests__/hydration/basic.spec.ts \
  -t '(reapplies select value after hydrated options update|hydrates the forced select value after option values)'
run_vitest 4 packages/runtime-vapor/__tests__/vdomInterop.spec.ts \
  -t '(syncs a .* select in a vapor slot when its vdom host updates|does not sync a select model removed while its vdom host updates|does not sync a new select removed with its vdom host in the same flush)$'
