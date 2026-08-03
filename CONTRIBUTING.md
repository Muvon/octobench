# Contributing

Thanks for contributing to `octobench`.

Most contributions in this repo are new benchmark cases. This guide focuses on that path.

## Development setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pre-commit
pre-commit install
```

Run checks before opening a PR:
```bash
pre-commit run --all-files
python3 -m compileall cli judges providers runners scoring
```

## Add a new case

### 1. Create the case folder
Use this path pattern:
`cases/<segment>/<sub_or_lang>/<case_name>/`

Example:
`cases/dev/oneshot/rust/uuid_parse_panic/`

### 2. Add required files
Each case should include:
- `case.yaml`
- `setup.sh`
- `quality.sh`
- `validate.sh`

Optional:
- `fixtures/` for static files used by scripts

You can start from `templates/case.yaml`.

Reference examples (current cases):
- `cases/dev/oneshot/rust/uuid_parse_panic/case.yaml`
- `cases/dev/oneshot/js/fastify_query_method/case.yaml`

### 3. Write a strong `case.yaml`
At minimum:
- Stable `id` (do not rename after merge)
- Clear task instruction
- Difficulty and category that match the work

Guidelines:
- Prefer concrete, testable tasks over vague prompts.
- Keep tasks scoped to one behavior/change.
- Avoid provider-specific hacks in prompt text.

### 4. Write scripts with clear roles
Use bash for all scripts:
- `#!/usr/bin/env bash`
- `set -euo pipefail`

#### `setup.sh` requirements (important)
`setup.sh` runs in an empty workspace prepared by the framework. It must fully create the scenario.

Expected pattern:
1. Clone one or more source repositories needed for the case.
2. Check out a pinned revision (commit SHA or immutable tag).
3. Apply case-specific mutations (delete files, edit files, add fixtures, corrupt state, etc.).

Rules:
- Do not rely on `master` / `main` / moving branches.
- Always pin to a stable revision.
- If multiple repos are needed, place them explicitly (current dir or subdirs) and document that in comments.
- It is valid to intentionally break or modify files after checkout if the case requires it.

Reference `setup.sh` examples:
- `cases/dev/oneshot/rust/uuid_parse_panic/setup.sh`
- `cases/dev/oneshot/js/fastify_query_method/setup.sh`

#### `quality.sh` expectations
`quality.sh` should check implementation quality signals (build/lint/tests), not final task correctness.

Good behavior:
- Prefer targeted checks relevant to the case.
- Keep logs compact and actionable.
- Print short summaries and clear failure reasons.

Avoid:
- Dumping very large logs to stdout/stderr by default.
- Running unrelated full-suite checks that create noisy output with little signal.

Reference `quality.sh` examples:
- `cases/dev/oneshot/rust/uuid_parse_panic/quality.sh`
- `cases/dev/oneshot/js/fastify_query_method/quality.sh`

#### `validate.sh` expectations
`validate.sh` should verify required behavior for the case (acceptance criteria).

Good behavior:
- Check concrete expected outcomes.
- Fail with precise, short error messages (`missing X`, `expected Y`, etc.).
- Be deterministic and resilient to non-functional formatting differences when possible.

Avoid:
- Overly brittle checks that reject correct behavior for cosmetic reasons.
- Verbose output that obscures the actual validation failure.

Reference `validate.sh` examples:
- `cases/dev/oneshot/rust/uuid_parse_panic/validate.sh`
- `cases/dev/oneshot/js/fastify_query_method/validate.sh`

Script conventions:
- Use `$CASE_DIR` to access case assets and fixtures.
- Keep output concise and diagnostic (errors should be obvious).

### 5. Validate locally
Run your case against at least one provider/model:
```bash
python3 -m cli.main run \
  --cases cases/<segment>/<sub_or_lang>/<case_name> \
  --providers codex,octomind \
  --models <benchmark-model-key> \
  --verbosity normal
```

Inspect:
- `results/<timestamp>/results.json`
- `results/<timestamp>/<case_id>/<setup>/logs/*`

## Case quality checklist
- Case is reproducible from scripts alone (no hidden manual steps).
- `setup.sh` creates deterministic initial state.
- `quality.sh` and `validate.sh` fail with actionable messages.
- Validation focuses on behavior, not brittle formatting.
- No secrets, API keys, or private data in fixtures/prompts.

## Pull request checklist
- Small, focused change set (one case or one clear improvement).
- Updated docs when behavior/structure changed.
- `pre-commit` passes locally.
- Included a short note in PR description on:
  - what the case measures
  - why it is useful
  - how you validated it

## Related docs
- `README.md`
- `docs/USAGE.md`
- `docs/EXTENDING.md`
- `docs/PROVIDER_INTERFACE.md`
