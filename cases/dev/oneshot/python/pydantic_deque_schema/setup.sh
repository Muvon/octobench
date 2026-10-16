#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/pydantic/pydantic"
BASE_SHA="2261ae19e2e09f792f06613360c83fc829238111"

git config --global --add safe.directory "$(pwd)" || true
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin

python -m pip install -q "uv==0.8.4"
UV_PROJECT_ENVIRONMENT=/opt/venv \
  uv sync --frozen --all-groups --all-packages --all-extras
VIRTUAL_ENV=/opt/venv \
  maturin develop --manifest-path pydantic-core/Cargo.toml --locked

python -c 'from pathlib import Path; import pydantic, pydantic_core, pydantic_core._pydantic_core as native; root = Path.cwd().resolve(); paths = {"pydantic": Path(pydantic.__file__).resolve(), "pydantic_core": Path(pydantic_core.__file__).resolve(), "pydantic_core._pydantic_core": Path(native.__file__).resolve()}; print(*(f"{name}: {path}" for name, path in paths.items()), sep="\n"); assert all(path.is_relative_to(root) for path in paths.values()), paths'
