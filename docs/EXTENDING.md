# Extending

## Add a new case
1. Create folder: `cases/<segment>/<sub_or_lang>/<case_name>/`
2. Add `case.yaml` using `templates/case.yaml`.
3. Add scripts (required names):
   - `setup.sh`
   - `quality.sh`
   - `validate.sh`
4. Add fixtures in `fixtures/`.

## Add a new provider (tool)
1. Create `providers/<provider>.py` and implement `Provider.run_task(..., executor)`.
2. Run the agent command via the injected `executor` (so it works in host and docker modes), not `subprocess` directly.
3. Return normalized fields in `ProviderRunResult`:
   - output text, exit code, elapsed_ms
   - input/cached/output/total tokens
4. Implement compact provider evidence via `build_provider_evidence(...)` when possible.
5. Follow the full provider contract in `docs/PROVIDER_INTERFACE.md`.
6. Register provider in `providers/factory.py`.
7. For `--executor docker`, add the tool's (pinned, prebuilt) binary to `docker/Dockerfile.agent`.

Octomind-specific:
- Provider runs octomind's stock coding agent `octomind run developer:general -m <model>`.
- Judge remains separate, as the Octomind `judge` role (`octomind run judge -m <model>`).

## Add benchmark model mapping + pricing
Edit `configs/models.yaml`:
- Add benchmark model key.
- Add per-1M pricing under `pricing`.
- Add provider mappings under `providers` for each provider implementation you use.

Example:
```yaml
models:
  gpt-5.2-codex:
    pricing:
      input: 1.75
      cached_input: 0.175
      output: 14.0
    providers:
      codex: gpt-5.2-codex
      octomind: openai:gpt-5.2-codex
```

## Notes on scripts
- Scripts are bash only.
- Output is **not parsed**; it is fed to the judge.
- `validate.sh` non-zero exit = hard fail.
- Use `$CASE_DIR` inside scripts to reference case assets (e.g., `$CASE_DIR/fixtures`).

Path convention:
- `segment` is a top-level benchmark class (example: `dev`, `edit`, `refactor`).
- `sub_or_lang` is segment-specific (for `dev`, use language like `rust`).
- `case_name` is a stable slug for the exact scenario.
