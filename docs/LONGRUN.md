# Long-Run Multi-Turn Benchmarks

Long-run cases test an agent's ability to work continuously in a single codebase
across multiple related tasks — mimicking a real developer's workflow where one
fix leads to the next. Each turn is a separate user instruction in the **same
agent session**, with source changes persisting across turns.

## Concept

A standard benchmark case is one-shot: one instruction, one validation. A
long-run case chains 5+ related commits from the same repository into a single
session. The agent solves turn 1, then turn 2 builds on the same codebase
(with the agent's changes from turn 1 still in place), and so on. Turns are
picked to share an intent thread — a maintainer fixing several related things
in one area — so the session feels like real continuous work, not disjoint
tasks.

This tests:
- **Context retention** — does the agent remember conventions it learned in turn 1?
- **State management** — do earlier changes break later turns?
- **Session continuity** — can the provider resume the same session efficiently?

## Case Structure

Each case lives in `cases/dev/longrun/<language>/<repo>/` and contains:

```
cases/dev/longrun/rust/tokio/
├── sequence.yaml   # turn definitions + metadata
└── setup.sh        # one-time repo checkout + build prep
```

### sequence.yaml

```yaml
id: longrun_rust_tokio
name: tokio async runtime fixes (5-turn sequence)
language: rust
system_prompt: |
  You are an autonomous software engineer working in an existing repository
  at the current directory. Resolve the requested task completely, as the
  project's maintainers would. When done, stop.
meta:
  repo: https://github.com/tokio-rs/tokio
  base_sha: <commit before the oldest PR>
  prs: [8109, 8274, 8260, 8279, 8222]
turns:
  - name: "Short title"
    instruction: |
      Describe what the agent should do. Derived from the PR's test diff
      following the derivability rule: everything the hidden tests assert
      must be derivable from this instruction alone.
    gold_sha: <merge commit SHA>
    test_paths:
      - path/to/test_file.rs
    test_command: |
      cargo test -p tokio-stream --test stream_peekable
```

### setup.sh

Checks out `base_sha`, prepares the build environment, then removes the remote
(so the agent cannot fetch gold commits):

```bash
REPO_URL="https://github.com/tokio-rs/tokio"
BASE_SHA="fe258f5e..."
git init -q .
git remote add origin "${REPO_URL}"
git fetch -q --depth 1 origin "${BASE_SHA}"
git checkout -q "${BASE_SHA}"
git checkout -q -B main
git remote remove origin
cargo build --tests 2>/dev/null || true
```

## How Validation Works

Per turn, the runner:

1. Sends the instruction to the agent (resuming the same session).
2. After the agent finishes, **re-adds origin** and fetches only the gold test
   files for that turn (`git checkout <gold_sha> -- <test_paths>`).
3. Runs `test_command`. Agent edits to test files are overwritten; only source
   changes persist.

This means the agent never sees the gold tests, but its source fix is validated
against them. A turn passes if `test_command` exits 0.

Each turn is scored separately (validation + judge + efficiency); the
sequence's headline score is the SUM of its turn scores
(`aggregate.sum_final_score`), with `avg_final_score` kept for comparing
sequences of different lengths.

## Running

```bash
# Validate all cases (dry-run, no providers needed)
python3 -m cli.longrun validate --sequences cases/dev/longrun

# Single sequence
python3 -m cli.longrun run \
  --sequence cases/dev/longrun/rust/tokio \
  --providers codex,octomind \
  --verbosity normal

# All sequences under a directory tree
python3 -m cli.longrun run \
  --sequences cases/dev/longrun \
  --providers codex,claude \
  --verbosity normal

# Using the run matrix config
python3 -m cli.longrun run \
  --sequence cases/dev/longrun/python/httpx \
  --config configs/run-matrix.yaml
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--sequence` | Path to a `sequence.yaml` or its directory |
| `--sequences` | Directory tree to scan for `sequence.yaml` files |
| `--providers` | Comma-separated provider names (codex, claude, octomind) |
| `--models` | Comma-separated benchmark model names |
| `--config` | Run matrix YAML (alternative to --providers/--models) |
| `--out` | Output directory (default: `results-longrun`) |
| `--executor` | `host` or `docker` |
| `--verbosity` | `quiet`, `normal`, or `debug` |

## Output

Results are written to `results-longrun/<timestamp>/`:

```
results-longrun/20260803-120000/
├── results.json                          # all sequence results
└── longrun_rust_tokio/
    └── codex__gpt_5/
        └── turns/
            ├── turn_1/logs/              # provider stdout/stderr, validate logs, judge output
            ├── turn_2/logs/
            └── ...
```

The `results.json` contains per-turn and aggregate metrics:

- Per turn: validation pass/fail, judge score, token usage, cost, elapsed time
- Per sequence: pass rate (X/5 turns), average score, total cost, total tokens

## Session Resumption

The runner passes `resume_session_id` to the provider on turns 2+. Provider
support:

| Provider | Resume mechanism |
|----------|-----------------|
| Claude   | `--resume <session_id>` |
| Codex    | `codex exec resume <session_id>` |
| Octomind | `-r/--resume` or `-n/--name` (named sessions auto-resume) |
| Opencode | No-op (no upstream resume support yet — runs each turn with fresh context; treat its column as a no-memory control) |

Cost/token accounting across resumed turns:
- claude: `total_cost_usd` and `usage` cover only the current invocation
  (verified empirically — resumed context arrives as cache reads); summing
  per-turn costs is correct.
- octomind: per-request fields are summed; the cumulative `session_tokens`
  field is deliberately ignored (it spans resumed sessions).
- codex: cumulative-vs-per-invocation semantics of `token_count` across
  `exec resume` are UNVERIFIED — check the raw jsonl of a 2-turn run before
  trusting summed codex tokens/costs.

## Available Cases

10 cases across 5 languages (2 per language), all turns fail-to-pass proven
in the agent image:

| Language | Repo | Turns |
|----------|------|-------|
| Python   | pydantic | 5 |
| Python   | pytest | 5 |
| JavaScript | fastify | 5 |
| JavaScript | axios | 5 |
| C++      | fmt | 7 |
| C++      | simdjson | 5 |
| PHP      | guzzle | 5 |
| PHP      | symfony | 5 |
| Rust     | clap | 5 |
| Rust     | tokio | 5 |

## Creating a New Long-Run Case

1. **Pick a repo** with active maintenance, deterministic tests, and a recent
   merge window (after model training cutoffs for contamination control).

2. **Mine 5 PRs** that touch both production source and tests. Verify each PR's
   test diff is deterministic (no network, no flaky timing).

3. **Find the base SHA**: the common ancestor of all 5 PR commits.

4. **Derive instructions** from the test diffs (not the source diffs). Every
   assertion in the gold tests must be derivable from the instruction alone.
   See the derivability rule in the repo's onboarding instructions.

5. **Create the case directory**:
   ```
   cases/dev/longrun/<lang>/<repo>/
   ├── sequence.yaml
   └── setup.sh
   ```

6. **Verify fail-to-pass**: `scripts/verify_longrun.sh <sequence_dir>` proves
   BOTH legs per turn in the agent image, cumulatively (each turn's gold fix
   stays applied for the next turn, mirroring the real bench flow): gold tests
   must FAIL before the fix and PASS after applying the gold source diff.
   `scripts/verify_all_longrun.sh` runs every sequence in parallel.

Provenance rules (learned the hard way):
- `gold_sha` MUST be the PR's true merge commit, reachable from the repo's
  default branch (`gh api repos/O/R/compare/BRANCH...SHA` → `behind` or
  `identical`). PR *branch-head* SHAs look identical in content but break
  provenance; unmerged/rejected PRs are disqualified outright.
- Every turn carries `pr_url` (or a commit URL when the PR record is gone).
- In multi-branch repos (symfony, guzzle), ALL turns must target the SAME
  base branch (`pulls/N --jq .base.ref`). Reachability from the default
  branch is NOT enough — bugfix branches merge upward, so a 6.4-targeted PR
  is "reachable" from 8.2 while its diff applies to 6.4-era code and its fix
  may depend on branch-only helpers.
- Check every turn's test files for INTERLEAVED commits: any upstream commit
  that touched a gold test file between base and gold injects assertions the
  sequence never covers (validation checks out whole files). Either add that
  commit as its own turn (best — fmt gained 2 turns this way), narrow the
  test command, or drop the file.
- setup.sh's BASE_SHA and meta.base_sha are duplicated — keep them in sync
  (the harness runs setup.sh; meta is what tooling reads).

Use `templates/sequence.yaml` as a starting template.
