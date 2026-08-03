# How we built a coding-agent benchmark out of real pull requests

*(working notes for a blog post — raw material, trim freely)*

## Why we didn't use an existing benchmark

Public coding benchmarks have two problems that kept biting us. First,
contamination: the popular suites are old enough that frontier models have seen
the fixes — sometimes literally, commit by commit — in training data. We caught
a model running `git show` on a commit hash it had no business knowing about.
Second, taste-grading: many benchmark tasks are graded by tests that assert an
implementer's arbitrary choices (an internal variable name, the exact wording of
an error message) that no reasonable task description would pin down. An agent
can write a maintainer-grade fix and fail because it phrased an error message
differently than the original author.

So we built our own: **25 tasks harvested from real, recently-merged pull
requests in respected open-source projects** — werkzeug, click, twig, carbon,
uuid, rayon, fmt, yaml-cpp, eslint, fastify, anyio, pydantic, symfony, guzzle,
commonmark, chrono, bytes, serde-json, catch2, spdlog, undici, pino,
pino-pretty. Five languages (python, php, rust, cpp, js), from one-line crash
fixes to multi-file features. Every fix was merged in 2026, mostly *after*
current model training cutoffs — several within days of harvesting. One case
(chrono's reversed date iterators) was merged the same morning we picked it.

## The anatomy of a task

Each case reconstructs the moment before the fix existed:

- **setup.sh** checks out the repository at the commit *before* the fix — as a
  single-commit shallow clone, so the fix is not hiding anywhere in the git
  object store — and prepares the toolchain (composer, cargo, cmake, npm, pip).
  The git remote is removed so the agent can't just fetch the upstream answer.
- The agent gets a **task prompt** and works in the repo like a hired
  contractor.
- **validate.sh** runs *after* the agent finishes: it fetches the merged fix's
  test files — which the agent has never seen — overwrites whatever the agent
  may have done to the test suite, and runs exactly those tests. The project's
  own tests, written by the project's own maintainers, decide pass or fail.
- An **LLM judge** separately grades the work quality from the diff and logs.

Before any case entered the benchmark it had to prove itself **fail-to-pass**:
the held-out tests must fail on the pre-fix code and pass when the real merged
fix is applied. No proof, no case.

## Two ways to write a task prompt

We wanted to test two realistic input scenarios:

**Reverse-engineered specs (20 tasks).** We ran a dedicated agent
(octomind's `developer:reverse-spec`) over each merged commit. It reads the
diff and reconstructs the task that plausibly produced it — at two fidelities:
the informal one-paragraph request as it probably arrived, and a fully
clarified spec with every ambiguity resolved the way the diff resolved it. Then
we curated by hand with one rule — **the derivability rule**: everything the
hidden tests assert must be derivable from the prompt. Bug fixes got the short
informal prompt (any correct fix passes). Features whose tests pin public API
names or exact output formats got the spec-tight version, because a real
requester *would* state a wire format.

**Original issues, verbatim (5 tasks).** For one task per language we used the
actual GitHub issue text as the prompt — trimmed only of fix-leaking sections
(one author had helpfully written "I have a PR ready that does X"). This tests
something different: turning a user-shaped bug report, sometimes with a
screenshot instead of expected output, into a maintainer-grade fix.

## What the tasks actually test

A few favorites, by the skill they isolate:

- **anyio cancel-scope spin** — a 4-line fix that requires understanding why an
  asyncio event loop pins a CPU core: cancellation delivery keeps rescheduling
  itself for a task that already finished. Tiny diff, deep async reasoning.
- **guzzle cookie prefixes** — 27 lines with three independent traps: prefixes
  match case-insensitively while names stay case-sensitive; a parsed cookie
  cannot tell "no Path attribute" from "Path defaulted to /" (you must re-read
  the raw header); and the guard must run *before* the store step or an invalid
  cookie can delete the valid one it was supposed to be blocked from touching.
  The naive `startsWith("__Secure-") && !secure` fix fails half the tests.
- **commonmark fenced-code tabs** — a user reported "code blocks sometimes lose
  their first character" with a screenshot. The root cause is column arithmetic
  for partially-consumed tab characters. The held-out fixtures include cases
  the issue never mentions — which only a true root-cause fix passes and a
  symptom-patch fails.
- **pino-pretty control characters** — sanitize terminal escapes across six
  render paths *without* touching escapes deliberately produced by the user's
  own custom prettifiers. Two hidden tests pass on the broken code and fail
  any over-broad fix: they exist purely to punish indiscriminate sanitizing.
- **spdlog source_loc lifetime** — a use-after-scope where five construction
  paths funnel through one view-rebuilding routine, and only two of them may
  copy. We build with AddressSanitizer so the pre-fix failure is a deterministic
  abort, not a heap-layout lottery.
- **bytes truncate(0)** — three lines that require understanding refcount
  lifecycle: emptying a shared buffer must release its hold so sibling clones
  can regain unique mutable access.

## The audit: eating our own dogfood

Before the final run we put every one of the 25 cases through an adversarial
audit — three reviewers reading every held-out assertion against every prompt.
It caught real problems:

- One case's tests asserted the **exact prose** of a new error message the
  issue never quoted. Both frontier agents produced perfect fixes — one even
  picked the same error-code number as the maintainer — and both failed on
  wording. We replaced the case and wrote the lesson into the harvesting rules:
  read the string assertions character by character.
- One case's hidden tests **contradicted the issue text** ("validation stays
  correct — only the schema is wrong") by demanding validation changes. We
  narrowed grading to what the issue actually reports.
- One case's held-out tests lived *inside* a source file, so restoring the
  gold tests wholesale would silently **revert a correct fix** written in that
  file. The validator now grafts only the test module.
- Assorted mechanical traps: a test-runner that ignores positional file
  arguments and runs the whole suite; a proc-macro that enumerates a test
  directory at compile time so a freshly-added test file silently doesn't run
  (the filter matches zero tests and "passes"); a PHPUnit config that turns a
  missing coverage driver into a failing exit code with all tests green.

The meta-lesson: **benchmark infrastructure fails in ways that look exactly
like model failures.** Every anomaly we investigated — a judge scoring 0 on a
passing run, a "solved" case with an empty diff — turned out to deserve a real
root-cause, and about half were ours, not the model's.

## Infrastructure war stories

- The LLM judge sometimes returned verdicts with the JSON head missing. Root
  cause: long answers arrive as multiple stream chunks and our parser kept only
  the last one. Then: judges "scoring" 0 with zero confidence — because our
  file-snapshot cap (4KB, fine for toy cases) meant real-repo diffs never
  reached the judge at all. It was grading green logs and no code, and honestly
  answered "cannot assess."
- An agent "finished" a task with the message *"Now I have a complete
  understanding. Let me create a plan and implement the fix."* — and a zero
  diff. In a non-interactive run, a text-only turn ends the session; the
  agent's own status said "in progress" and nothing questioned the hand-back.
  We added a deterministic guard: if a turn ends with no action while the
  agent's self-reported status is still *exploring/progressing*, an advisory
  note sends it back to work, bounded by the existing verification budget. In
  the final run that failure mode disappeared.
- Overnight, five cases died to provider 500/529 overload errors. The harness
  originally aborted the whole run on a provider failure; we made failures
  per-case records with an automatic retry-and-merge pass. Also: the disk
  filled at 3am, an SSH ban locked us out of our own server for an hour
  (lesson: don't poll every two minutes), and a "quick fix" edit to a bash
  script that was *currently executing* taught us that bash re-reads scripts
  at byte offsets.

## The contenders

Four agents, each at its stock, out-of-the-box invocation:

| agent | model | notes |
|---|---|---|
| claude code | claude-opus-5 | Anthropic caching: ~97% of context re-reads billed at 1/10 input price |
| octomind | glm-5.2 via Ollama cloud | **no prompt caching** — every re-read at full list price |
| codex | gpt-5.6-sol | OpenAI implicit caching |
| opencode | glm-5.2 via Ollama cloud | same model + endpoint as octomind — a pure harness A/B |

## Results

| | solved | judge Σ | cost | wall time |
|---|---|---|---|---|
| **octomind + glm-5.2** | **24/25** | **2264** | $63.43 | 3.6h |
| claude code + opus-5 | 23/25 | 2262 | $81.79 | 6.7h |
| codex + gpt-5.6-sol | 21/25 | 2127 | **$14.86** | **1.0h** |
| opencode + glm-5.2 | 19/25 | 2093 | $129.54 | 3.3h |

What the table says:

1. **The harness matters as much as the model.** Same model, same endpoint,
   same prices: octomind solved 24, opencode 19 — at *half* the cost. The
   difference is context discipline (opencode pushed 30M input tokens through
   one task where octomind needed 8M) and supervision: the cases opencode
   dropped are exactly the deep-root-cause and multi-trap ones where an
   unsupervised agent declares victory too early.
2. **glm-5.2 beat opus while paying full price for every token.** Opus re-read
   its context at cache rates all run long; glm re-bought it at list price and
   still came out cheaper *and* ahead on solves. On any cache-enabled endpoint
   the cost gap becomes a chasm.
3. **Codex is a speed demon with a thoroughness tax.** 2–4 minutes per case,
   $0.59 median — and all four of its failures are cases that punish not
   checking one more caller, one more surface, one more trap.
4. **No task was impossible** — every case was solved by at least one agent.
   And failure classes were remarkably clean: the trust-boundary case (don't
   sanitize trusted output) caught opus, codex, *and* opencode; the deep
   root-cause parser case caught everyone except octomind; and the one case
   both glm harnesses failed identically is a genuine model blind spot
   (byte-exact emitter formatting), not a harness artifact.

Full data, per-case logs, and a complete reproduction guide: `BENCHMARK.md`
in the repo. The case-harvesting pipeline — including the reverse-spec agent
and the derivability rules — is documented so the set can keep growing as
models' training cutoffs advance. That's the point: a benchmark you can
re-harvest is a benchmark that can't go stale.
