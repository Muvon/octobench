# Provider Interface

This document defines the required provider contract for consistent and fair benchmarking.

## Goals
- Keep provider outputs comparable across tools.
- Normalize token/cost semantics.
- Provide compact, evidence-focused traces for judging.

## Required API

Provider implementations must follow `providers/base.py`:

1. `run_task(prompt, workdir, provider_model, session_name, executor) -> ProviderRunResult`
2. Optional override: `build_provider_evidence(run_result) -> str`

Run the agent command via the injected `executor` (`runners/executor.py`), not
`subprocess` directly — this is what makes a provider work identically in host and
docker modes:
- `executor.run(argv, env_overrides=..., input_text=prompt)` → `ExecResult(stdout, stderr, exit_code)`
- `executor.container_workspace()` → the workdir as seen by the command (host path or `/workspace`/`/testbed`); use it for any path you pass to the CLI.
- `executor.workspace_host_path()` → host path, to read back any files the CLI wrote.
- `executor.octomind_config_path()` → the `OCTOMIND_CONFIG_PATH` valid in that environment.

## `ProviderRunResult` Contract

Required fields:
- `stdout`: final assistant message text (best effort)
- `stderr`: tool stderr or execution error summary
- `exit_code`: process/task result code (`0` success)
- `elapsed_ms`: wall-clock runtime in milliseconds

Token fields (optional but strongly recommended):
- `semantics`: `separate_reasoning_v1` in persisted result records
- `input_tokens`: non-cached input tokens only
- `cached_input_tokens`: cached input tokens
- `output_tokens`: visible/non-reasoning output tokens
- `reasoning_tokens`: reasoning tokens (if provider exposes them)
- `total_tokens`: total tokens; should include cached+reasoning when available

Provider trace (optional structured data):
- `provider_trace`: compact dict used to build judge evidence

## Token Semantics (Fairness Critical)

Use canonical semantics across all providers:
- `input_tokens` excludes cached input.
- `cached_input_tokens` is separate.
- `output_tokens` is response/output only.
- `total_tokens = input_tokens + cached_input_tokens + output_tokens + reasoning_tokens` when reasoning is known.

If a provider exposes only aggregate input:
- subtract cached from input when cached is available.
- never double-count cached tokens.

## Evidence Contract

`build_provider_evidence(run_result)` should return a short string for judge context.

Rules:
- Evidence only; no extra narrative.
- Keep it compact and bounded.
- Prefer stable sections so judges can parse consistently.
- Do not include large raw logs or blobs.

Recommended sections:
- `provider: <name>`
- `assistant_messages:` list of short messages
- `tool_intents:` list of tool calls/intents (name + short args summary)
- `tool_results:` optional, compact success/failure signals

Size guidance:
- Truncate each item (e.g. 150-400 chars).
- Cap number of items per section.
- Keep total evidence string small enough for judge context budget.

## Error Handling Requirements

- Never throw uncaught exceptions from provider execution paths.
- On execution failures, return non-zero `exit_code` and meaningful `stderr`.
- Return best-effort partial telemetry if available.

## Registration Requirements

For a new provider:
1. Add implementation in `providers/<name>.py`.
2. Register in `providers/factory.py`.
3. Add provider model mappings under each benchmark model in `configs/models.yaml`.
4. Verify one dry run with `python3 -m cli.main run ...`.

## Consistency Checklist

Before merging a provider:
- `run_task` returns all required fields.
- token semantics follow canonical contract.
- evidence is compact and not noisy.
- failure behavior is explicit in `exit_code`/`stderr`.
- results are comparable with existing providers.
