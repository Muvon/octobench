# octobench multi-domain benchmarks

This directory holds one YAML config per benchmark. Each binds to an adapter
**engine** and is run by the unified runner:

```bash
python3 -m cli.bench --list                                   # catalog (domain, engine, fit, ready)
python3 -m cli.bench --benchmark <name> --limit N \
        --providers claude --models claude-sonnet-4           # run across the chosen setup(s)
python3 scripts/summary.py results-bench                      # comparison table
```

A "setup" is the thing octobench compares: **framework (claude / codex / octomind)
× model × executor mode (host / docker)**. A benchmark supplies the *cases*; the
runner produces the per-setup ranking. Pick setups with `--providers/--models` or a
run-matrix (`configs/run-matrix.bench.yaml`).

Notes:
- Pair each `--models` key with a `--providers` it maps to in `configs/models.yaml`
  (`claude`+`claude-sonnet-4`, `codex`+`gpt-5.2-codex`, `octomind`+`minimax-m3`).
- `--no-judge` skips the LLM judge; objective benches (`mcq`/`final_answer`/`constraint`)
  still score from their verdict.
- The `claude` provider uses your local claude login (no key). The `octomind` provider
  AND the judge route through octohub — set `OCTOHUB_API_URL=https://octohub.muvon.ltd`
  and `OCTOHUB_API_KEY` in the run environment (a non-interactive `ssh host 'cmd'` shell
  won't inherit interactive exports — put them in the box's profile for remote runs).

## Engines

| engine | verdict | use for |
|---|---|---|
| `qa` | objective (mcq / final_answer / constraint) **or** judge (judge_text) | single-turn QA: knowledge, math, instruction-following, factuality, creative, finance/legal QA |
| `docker_task` | programmatic (run a verify command in a container) | env-required: CTF/CVE, terminal, EHR/FHIR, SQL, research-code |
| `swebench_live` | repo `FAIL_TO_PASS`/`PASS_TO_PASS` tests | real post-2024 GitHub issues (the gold standard) |

`fit` mirrors the landscape report: `objective-verdict` (maps to a hard
`validate.sh`-style gate, contamination-resistant), `judge-scorable` (LLM-judge
path), `static-qa` (objective but contaminated/saturated — baseline only),
`needs-harness` (needs an upstream interactive env).

## ready = data → runs now

Benches marked **data** in `--list` run today against Hugging Face / inline data
(you only need a model API key / login for the framework under test):

- **frontier knowledge:** `mmlu_pro`, `supergpqa`, `mmlu` (MCQ), `simpleqa_verified` (factuality)
- **math:** `aime25` (post-cutoff, low contamination), `math500`
- **instruction-following:** `ifeval` (programmatic constraint checkers)
- **health:** `medxpertqa` (board-level MCQ)
- **finance:** `financebench` (judge vs reference)
- **marketing/creative:** `marketing_creative` (judge rubric, inline briefs)
- **writing:** `writingbench` (per-query WritingBench rubrics, official JSONL over HTTP)
- **legal:** `legal_qa` (judge rubric, inline starters)

## ready = needs-image / docker → wire the upstream env

These are `docker_task` / `swebench_live` configs whose verdict needs an upstream
Docker image or harness. Each config's `notes` field says exactly how to wire it.

- **coding:** `swebench_live` (works with the SWE-bench-Live per-instance images), `terminal_bench`
- **cyber:** `ctf_smoke` (self-contained proof — runs with just `octobench-agent:latest`), `cve_bench`, `cybench`
- **health:** `medagentbench` (FHIR image, synthetic patients)
- **science:** `researchcodebench`
- **data:** `livesqlbench`
- **orchestration:** `tau2_bench`
- **browser:** `webarena`
- **computer-use:** `osworld`

Prove the docker path end-to-end with no external infra:

```bash
docker build -f docker/Dockerfile.agent -t octobench-agent:latest docker
python3 -m cli.bench --benchmark ctf_smoke --executor docker --limit 1
```

## Add a benchmark

Create `configs/benchmarks/<name>.yaml` with an `engine` key. No code needed for
the common cases:

**Objective MCQ from Hugging Face:**
```yaml
engine: qa
name: my_mcq
domain: <domain>
fit: static-qa
mode: mcq
source: hf
dataset: <org/dataset>
hf_config: default
split: test
fields: { question: question, choices: options, answer: answer }
```
`choices` may be a list field, a letter-keyed dict, `options_fields: [opa,opb,...]`,
or `correct` + `incorrect`/`incorrect_fields` (assembled + rotated).

**Objective final answer:** `mode: final_answer`, `match: math|numeric|string|set`,
`fields: { question: ..., answer: ... }`.

**Programmatic instruction-following:** `mode: constraint`, fields mapping
`instruction_id_list` + `kwargs` (IFEval schema) or inline `constraints`.

**Judge-scored open generation:** `mode: judge_text`, set a `rubric`, map a
`reference` field (or inline `instances`).

**Env-required (objective in a container):** `engine: docker_task`, set `image`,
`workdir`, and per-instance `setup_cmds` / `verify_cmds` / `success_regex` (matched
against agent output + verify output) or `success_exit: true`.

Validate everything offline (registry + configs + matchers + scoring) with:

```bash
python3 scripts/bench_selftest.py
```
