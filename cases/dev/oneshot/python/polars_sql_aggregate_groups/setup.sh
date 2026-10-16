#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pola-rs/polars"
BASE_SHA="f9452aa4fb28e834a092169787acabead8a9a6de"

git config --global --add safe.directory "$(pwd)"
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

# The upstream AI contribution policy governs issues and pull requests, not this
# local task; GOLD removes it so no client declines the work because of it.
git rm -q AI_POLICY.md
git -c user.name=octobench -c user.email=octobench@localhost commit -q -m "Remove upstream AI contribution policy"

# Upstream leaves reference-engine dependencies floating; freeze the test closure.
python -m pip install --no-deps \
  pip==25.2 setuptools==80.9.0 wheel==0.45.1 \
  maturin==1.13.0 patchelf==0.17.2.4 \
  pytest==9.0.3 pytest-xdist==3.8.0 execnet==2.1.1 \
  iniconfig==2.1.0 packaging==25.0 pluggy==1.6.0 pygments==2.19.2 \
  hypothesis==6.140.2 attrs==25.3.0 sortedcontainers==2.4.0 \
  numpy==2.3.3 pyarrow==21.0.0 duckdb==1.4.1 \
  pandas==2.3.2 python-dateutil==2.9.0.post0 pytz==2025.2 tzdata==2025.2 six==1.17.0

rustup toolchain install nightly-2026-09-01 --profile minimal
export RUSTUP_TOOLCHAIN=nightly-2026-09-01
export CARGO_BUILD_JOBS=6
export VIRTUAL_ENV=/opt/venv

python -m pip install --no-deps --no-build-isolation -e py-polars
cargo fetch --locked
maturin develop --manifest-path py-polars/runtime/polars-runtime-32/Cargo.toml --locked --offline

python - <<'PY'
from pathlib import Path
import duckdb
import polars
import polars._plr as native
import pyarrow

root = Path.cwd().resolve()
for module in (polars, native):
    path = Path(module.__file__).resolve()
    print(f"{module.__name__}: {path}")
    if not path.is_relative_to(root):
        raise SystemExit(f"Expected workspace module: {path}")
PY
