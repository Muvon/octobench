# Octobench Batch 5 Mining Report — "Public Workflow / Black-Box Contract"

Date of mining: 2026-08-01.

> **Implementation status.** The ten case directories described here are now
> scaffolded under `cases/dev/*/*/` in this same PR (`case.yaml` + `setup.sh` +
> `quality.sh` + `validate.sh`, ten new dirs, `dev5_*` ids). **None has been
> executed.** Every `case.yaml` carries `meta.verified: false`; the scripts have
> been syntax-checked (`bash -n`) and their base/gold SHAs verified against the
> GitHub API, but no `setup.sh`, `quality.sh` or `validate.sh` has been run and
> no fail-to-pass leg has been proven. `scripts/verify_case.sh` on all ten is the
> gate before any of these are benchmarked.
>
> One Docker change is required: **`libcurl4-openssl-dev`** for the cpp-httplib
> case (`test/CMakeLists.txt` does `find_package(CURL REQUIRED)`). Its `setup.sh`
> installs it defensively so the case is runnable before the image is rebuilt.

---

## 1. Current-corpus gap analysis

Live inventory of `cases/dev` (`find cases/dev -name case.yaml | wc -l` → **40 cases**):

| Language | Cases | Repositories already used |
|---|---|---|
| cpp | 8 | catchorg/Catch2, fmtlib/fmt, opencv/opencv, redis/redis, simdjson/simdjson, gabime/spdlog, jbeder/yaml-cpp ×2 |
| js | 8 | axios, eslint, fastify, pinojs/pino, pinojs/pino-pretty, facebook/react, nodejs/undici, webpack |
| php | 8 | cakephp, briannesbitt/Carbon, thephpleague/commonmark, composer/composer, thephpleague/flysystem, guzzle/guzzle, symfony/symfony, twigphp/Twig |
| python | 8 | agronholm/anyio ×2, celery, pallets/click, fastapi, pydantic, tornadoweb/tornado, pallets/werkzeug |
| rust | 8 | tokio-rs/bytes, chronotope/chrono, rayon-rs/rayon, rustls, serde-rs/json, tokio-rs/tokio, toml-rs/toml, uuid-rs/uuid |

**Scenario mix in the live tree** (`meta.scenario`): crash-fix ×4, bug-fix ×3, feature ×4,
parser-* / *-spec-compliance / parser-validation / parser-boundary / parser-tab-arithmetic ×7,
security-* ×5, concurrency-* ×4, resource-lifecycle ×2, plus one each of
error-handling, error-handling-robustness, lifetime-ub, falsy-boundary,
deserialization-round-trip, schema-validation-divergence, protocol-bug-fix,
transport-config-boundary, encoding-security, user-facing-diagnostics, simple-edit.

**Prompt sources**: 26 reverse-spec (default), 10 `human-prompt`, 4 `original-issue`.

**What is over-represented**: single-call library internals. 17 of 40 cases are
"feed this one input to this one function and check the value/exception" —
parsers (7), crash fixes (4), and isolated algorithm/boundary fixes. Only two
cases (`webpack_lazy_backend_shutdown`, `bytes_truncate_release`) reproduce
through a *lifecycle*, and only one (`composer_policy_source`) is driven from a
CLI's user-visible output.

**What is absent**: nothing in the corpus tests configuration precedence, an
env-var contract, a restart/cancel boundary, filesystem cleanup or artifact
survival, a fake-vs-real mode compatibility guarantee, idempotency of a repeated
user operation, or a CLI's stdout/exit-status contract as the *primary*
assertion surface. This batch targets exactly that band: every case reproduces
through a documented public surface (CLI flag, config file, HTTP header, public
SDK call, on-disk artifact) and most require **more than one user action** to
observe.

---

## 2. Contamination boundary

**Newest configured benchmark model.** `configs/run-matrix.cases.yaml` — the
matrix used for these internal real-commit cases — runs `claude-opus-5` and
`glm-5.2`. `configs/models.yaml` also registers newer-numbered entries
(`gpt-5.6-sol`, `gemini-3.5-flash`, `minimax-m3`, `kimi-k2.6`, `deepseek-4-pro`).

**Cutoff and source.** Authoritative: Anthropic's model documentation,
"Latest models comparison" table
(<https://platform.claude.com/docs/en/about-claude/models/overview>), fetched
2026-08-01:

| Model | Reliable knowledge cutoff | Training data cutoff |
|---|---|---|
| Claude Opus 5 | May 2026 | **May 2026** |
| Claude Fable 5 | Jan 2026 | Jan 2026 |
| Claude Sonnet 5 | Jan 2026 | Jan 2026 |
| Claude Haiku 4.5 | Feb 2025 | Jul 2025 |

Claude Opus 5's **May 2026** training-data cutoff is the latest documented
cutoff among configured models and is therefore the binding boundary.

**Uncertainty, stated honestly.** I could not find an authoritative published
training cutoff for `gpt-5.6-sol`, `glm-5.2`, `gemini-3.5-flash`, `minimax-m3`,
`kimi-k2.6`, or `deepseek-4-pro`. I did **not** invent one.

**Policy used.** Conservative merge window: **every candidate merged on or after
2026-07-01**, i.e. the last ~30 days. That clears the documented May 2026 Opus 5
cutoff by roughly two months and gives headroom against the undocumented
cutoffs. All ten selections merged between **2026-07-02 and 2026-08-01**; the
newest (poetry) merged **the morning of the mining run**.

---

## 3. Broad search log

Method: `gh api repos/<r>/pulls?state=closed&sort=updated` filtered to
`merged_at >= 2026-07-01`, then per-PR inspection of files, reviews, linked
issue, and CI check-runs. 46 repositories scanned.

### C / C++ (13 repos scanned)
| Repo | Verdict |
|---|---|
| libgit2/libgit2 | **Accepted** (#7291). Extraordinary trust (powers GitHub, GitLab, Azure DevOps); new standalone test file; clar suites run selectively. |
| yhirose/cpp-httplib | **Accepted** (#2479). Public HTTP client/server contract, deterministic loopback test, fast build. Caveat: single-maintainer review (§8). |
| CLIUtils/CLI11 | Rejected. #1384/#1363 bodies are literally labelled ":robot: _AI text below_ :robot:" and self-merged with zero reviews. Fails human-authored + real-review. |
| google/googletest | Rejected. #5041 (shuffle order) and #5039 (premature-exit segfault) are both **production-only, no tests**. |
| ninja-build/ninja | Rejected as primary (#2680): superb review record (62 review comments, two maintainers requested changes) but +647/−212 with a 444-line rewrite of `graph.cc`. Held as alternate. |
| nlohmann/json | Rejected. July merges are almost all malformed-binary-input validation (would blow the ≤2 parser cap) and the single-header test suite costs 10+ min to compile per binary. |
| libuv/libuv | Rejected. #5206 is the only one with tests and its author discloses "I used Codex to help investigate, implement, and test this change" — not clean human work. #5213 (Windows-only) and #5186 (poll bits) ship no tests. |
| curl/curl, facebook/zstd, rui314/mold, abseil/abseil-cpp, google/re2, google/leveldb, p-ranav/argparse, marzer/tomlplusplus, doctest/doctest, open-source-parsers/jsoncpp | Rejected: no qualifying merged PR in window, or docs/CI-only, or single-maintainer churn (doctest = 19 self-merges). |

### JavaScript / TypeScript (11 repos scanned)
| Repo | Verdict |
|---|---|
| honojs/hono | **Accepted** (#5147). Pure HTTP header contract, maintainer-approved, vitest, fast install. |
| vitejs/vite | **Accepted** (#22992). Restart-during-update race, approved by two core maintainers (bluwy, sapphi-red). |
| expressjs/express | Rejected (#7366, QUERY conditional revalidation). Clean and two-approved, but the gold test guards on `shouldSkipQuery(process.versions.node)` — on the image's Node 22 the test may *skip*, which would make it pass at base and destroy fail-to-pass. Held as alternate pending a Node-version check. |
| prettier/prettier | Rejected. July window is ~70% renovate bots; #19725 (template-literal idempotency) is attractive but assertions are snapshot-file diffs, poor for a hidden-test graft. |
| sindresorhus/execa | Rejected. Excellent lifecycle surface (#1256 killDescendants, #1241 fd/ipc) but every PR is authored **and** merged by the sole maintainer — no independent review evidence. |
| mochajs/mocha | Rejected. Mid-flight `yargs` → `util.parseArgs` migration (#6124/#6125/#6164 breaking changes); base state unstable. |
| motdotla/dotenv | Rejected. Self-authored/self-merged, and July includes `.env.vault` removals — unstable base. |
| socketio/socket.io, yargs/yargs, jestjs/jest, vitest-dev/vitest | Rejected: too few qualifying merges in window, or monorepo setup cost with no better surface than vite. |

### PHP (12 repos scanned)
| Repo | Verdict |
|---|---|
| doctrine/dbal | **Accepted** (#7392). Lead maintainer (morozov) approved after review rounds; runs on SQLite by default → fully offline. |
| laravel/framework | **Accepted** (#60916). Caveat: Laravel merges without GitHub reviews (§8). |
| laravel/framework #60877 | **Rejected on derivability** (see §8) — the schedule:list timezone converter. Its data provider pins ~40 maintainer-chosen cron *normalization policies* (`0 */2 * * *` → `0 1-23/2 * * *`; `0 1 31 * *` → `0 16 30 1,3,5,7,8,10,12 *`; February left unconverted; wildcard-day merges vs fixed-day splits). No user-level prompt can state these without dictating the algorithm. |
| sebastianbergmann/phpunit | Rejected. Every merge in window is renovate[bot]. |
| phpstan/phpstan-src | Rejected. Window is dominated by `ondrejmirtes` internal-engine refactors and `phpstan-bot` commits; assertions are analyser-internal. |
| api-platform/core | Rejected (#8348 HEAD-skips-body). 22 files, introduces a new maintainer-named config key → derivability leak. |
| nikic/PHP-Parser | Rejected (#1157/#1156). 1-line production change into a `.test` fixture; no review. |
| Seldaek/monolog, rectorphp/rector, slimphp/Slim, mockery/mockery, vlucas/phpdotenv, ramsey/uuid, phpoffice/phpspreadsheet, pestphp/pest, yiisoft/yii2 | Rejected: dependabot-only windows, no merges, or DB-server-dependent tests (yii2's window is almost entirely Oracle/PostgreSQL/MySQL metadata work). |

### Python (7 repos scanned)
| Repo | Verdict |
|---|---|
| pytest-dev/pytest | **Accepted** (#14730). User-reported issue #14724, maintainer-approved, `pytester` gives an end-to-end CLI assertion. |
| python-poetry/poetry | **Accepted** (#10982). Merged the morning of the mining run; maintainer (radoering) approved; fixes user issue #10425. |
| pytest-dev/pytest #14331 | **Rejected on derivability** — see §8. The hidden test does `from _pytest.pathlib import _chmod_rwx`, a private helper *created by the gold patch*. Unpassable without guessing a maintainer-chosen private name. |
| pypa/pip | Rejected (#14204 CI rich-interactivity). 5 files changed but the only test delta is `+1/−1` in `tests/unit/test_network_session.py` — no coverage of the new behavior, and zero reviews. |
| psf/black | Rejected. #5192 (empty cache files) is a one-token `except` addition. #5211 (BLACK_NUM_WORKERS validation) is a good surface but carries **zero** review approvals. Both held as alternates. |
| encode/httpx | Rejected. No merges in window. |
| django/django | Not scanned in depth — merge path is heavily Trac/ticket-driven and the batch already had two strong Python picks. |

### Rust (7 repos scanned)
| Repo | Verdict |
|---|---|
| seanmonstar/reqwest | **Accepted** (#3064). seanmonstar approved; fixes user issue #2839; 30/30 CI green on PR head. |
| BurntSushi/ripgrep | **Accepted** (#3496). BurntSushi approved; fixes issue #2565. |
| clap-rs/clap | Rejected (#6409 pwsh detection). 18 review comments from epage — great review evidence — but the diff touches **production source only, no tests**. |
| astral-sh/uv | Rejected. Enormous velocity but a large share of July merges are `astral-automations-bot[bot]` promotions; release-build cost is high. |
| astral-sh/ruff | Rejected. Same bot problem plus a July window dominated by mechanical "Remove unused APIs from …" sweeps. |
| rust-lang/cargo, tokio-rs/axum | Not selected — cargo's build cost is prohibitive; tokio-rs already owns two corpus repos. |

---

## 4. Final ten

All SHAs are full 40 characters. "Base" = first parent of the gold commit.

| # | Lang | Lane | Repository | PR / issue | Merged (UTC) | Human & review proof | User-visible workflow | Category | Base SHA | Gold SHA | Production paths | Hidden test paths | Selective test command | Est. setup / validate | Why it is new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | cpp | A | [libgit2/libgit2](https://github.com/libgit2/libgit2) | [PR #7291](https://github.com/libgit2/libgit2/pull/7291) (follow-up to [#7281](https://github.com/libgit2/libgit2/pull/7281)) | 2026-07-18 08:12 | Merged by core maintainers; **PR head CI 21/21 green** across 19 build matrices incl. 4 sanitizers. (Post-merge `main` run shows 19 infra failures from the concurrent CI-credential rotation — `main` is green again today.) | `git log -- README` equivalent via `git_revwalk` + `git_pathspec` silently omits the repository's initial commit | 3 (path handling) | `32b564e63f9639eaf5ee90fb7a95b3a650156cbd` | `9e1c61e0924de72d44ecabe43ccb02820ca68981` | `src/libgit2/revwalk.c` | `tests/libgit2/revwalk/pathspec.c` (**new file**) | `./build/libgit2_tests -srevwalk::pathspec` | ~4 min / ~1 min | First C-history-traversal case; first case whose repro is "compare against `git log`" |
| 2 | cpp | B | [yhirose/cpp-httplib](https://github.com/yhirose/cpp-httplib) | [PR #2479](https://github.com/yhirose/cpp-httplib/pull/2479) | 2026-07-02 01:18 | Maintainer-merged; **26/26 CI green**; PR contains a reasoned RFC-3986 argument | `cli.set_path_encode(false)` is documented to send the caller's target verbatim, but the query half is still decoded and re-encoded, corrupting pre-encoded payloads (`%20`→`+`) | 2 (config → runtime) | `0ae93881b44bf94437843403bfcdc4f50445992e` | `3fe32b63b42d7b273cd4d76d69df0097560375d6` | `httplib.h` | `test/test.cc` | `cd build/test && ./httplib-test --gtest_filter='PathUrlEncodeTest.*'` | ~5 min / ~2 min | First client-config→wire-format case; first loopback HTTP case in cpp |
| 3 | js | A | [honojs/hono](https://github.com/honojs/hono) | [PR #5147](https://github.com/honojs/hono/pull/5147) | 2026-07-24 08:48 | **yusukebe (lead) APPROVED**; 17/17 CI green | Enabling both `contentSecurityPolicy` and `contentSecurityPolicyReportOnly` where either uses a nonce makes every request return **500** | 8 (HTTP headers/status) | `c85aead088659b98b8d05a1187a07d064e12ffe6` | `402eb3abe561914f41ee0f8e37f1d7f211f1ee51` | `src/middleware/secure-headers/secure-headers.ts` | `src/middleware/secure-headers/index.test.ts` | `npx vitest run src/middleware/secure-headers/index.test.ts` | ~2 min / ~30 s | First response-header-contract case; first "two headers must not cross-contaminate" |
| 4 | js | B | [vitejs/vite](https://github.com/vitejs/vite) | [PR #22992](https://github.com/vitejs/vite/pull/22992) | 2026-07-24 05:49 | **bluwy APPROVED + sapphi-red APPROVED** (two core maintainers); 12 success / 2 skipped | Editing a file while a `.env`/config change restarts the dev server crashes Vite with `TypeError: Cannot set properties of undefined (setting error)` | 4 (restart after partial failure) | `95a3cdab83e1125b03d2e8dd942fb6b64209e5fa` | `b1186c36d06bb94941c58e8272fc4acb8512c93b` | `packages/vite/src/node/server/hmr.ts` | `packages/vite/src/node/server/__tests__/hmr.spec.ts` (**new file**) | `pnpm --filter vite exec vitest run src/node/server/__tests__/hmr.spec.ts` | ~6 min / ~1 min | First restart/staleness case; first case where the contract is "abandon work in flight" |
| 5 | php | A | [doctrine/dbal](https://github.com/doctrine/dbal) | [PR #7392](https://github.com/doctrine/dbal/pull/7392) | 2026-07-24 13:40 | **morozov (lead) APPROVED** after 6 review comments; **30/30 CI green** | Altering a table obtained from `introspectTableByUnquotedName()` on SQLite silently drops **every** index and foreign key; rows survive, constraints vanish, no error | 5 (two representations must behave alike) | `6d8aa68d21f903101b6632e76a40a8626e61c56a` | `34b62998bf626326184bc25f58b39518d04928ce` | `src/Platforms/SQLitePlatform.php` | `tests/Functional/Schema/SchemaManagerFunctionalTestCase.php` | `vendor/bin/phpunit tests/Functional/Schema/SQLiteSchemaManagerTest.php` | ~3 min / ~1 min | First schema-migration / DDL round-trip case; first "introspected vs in-memory object" compat case |
| 6 | php | B | [laravel/framework](https://github.com/laravel/framework) | [PR #60916](https://github.com/laravel/framework/pull/60916) | 2026-07-29 14:35 | Merged to `13.x` by maintainers; **30/30 CI green**. ⚠ No GitHub review record — Laravel's merge process is maintainer-push (§8) | `Queue::fake()` + bulk dispatch ignores `#[Delay]` and runtime `->delay()`, so tests that pass against a real driver fail against the fake | 5 (fake vs real driver parity) | `91eee4b8a7c4f4301700fa359de92898528bb917` | `af9d320df90c0a69c230d35c17370e7db6a4035d` | `src/Illuminate/Support/Testing/Fakes/QueueFake.php` | `tests/Support/SupportTestingQueueFakeTest.php` | `vendor/bin/phpunit tests/Support/SupportTestingQueueFakeTest.php` | ~4 min / ~40 s | First test-double-parity case; first queue/delay lifecycle case |
| 7 | python | A | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) | [PR #14730](https://github.com/pytest-dev/pytest/pull/14730) / [issue #14724](https://github.com/pytest-dev/pytest/issues/14724) | 2026-07-23 09:36 | **nicoddemus (core) APPROVED**; **30/30 CI green**; issue filed by an outside user (dprada) | `pytest --no-summary` silently disables the `pytest_terminal_summary` hook, so third-party plugin summaries (e.g. coverage) disappear too | 1 (CLI stdout contract) | `85003621822f9c10063940068ccacc9c12b8c73f` | `6f1b078537cf4ab14d0a7b29972c4e73f23a9011` | `src/_pytest/terminal.py` | `testing/test_terminal.py` | `pytest testing/test_terminal.py -k "no_summary"` | ~2 min / ~30 s | First hook-vs-flag scoping case; first "a flag must narrow, not broaden, its effect" |
| 8 | python | B | [python-poetry/poetry](https://github.com/python-poetry/poetry) | [PR #10982](https://github.com/python-poetry/poetry/pull/10982) / [issue #10425](https://github.com/python-poetry/poetry/issues/10425) | **2026-08-01 07:56** | **radoering (core) APPROVED** with review comments; **30/30 CI green** | A dependency pinned to a `priority = "explicit"` source is never reported by `poetry show --outdated`, even when that source has a newer version | 1 (CLI stdout, table + JSON) | `3a95c37c5d5ec600556f519e60e4340f35bbcac1` | `62018d105562e1365bf79607edcc29ed794e4635` | `src/poetry/console/commands/show.py` | `tests/console/commands/test_show.py` | `pytest tests/console/commands/test_show.py -k outdated` | ~3 min / ~1 min | Newest PR in the batch (same-day); first source-priority/lockfile-provenance case |
| 9 | rust | A | [seanmonstar/reqwest](https://github.com/seanmonstar/reqwest) | [PR #3064](https://github.com/seanmonstar/reqwest/pull/3064) / [issue #2839](https://github.com/seanmonstar/reqwest/issues/2839) | 2026-07-13 13:11 | **seanmonstar (owner) APPROVED**; **30/30 CI green on PR head**; review feedback visibly changed the approach (kept `Kind::Decode` instead of reclassifying) | A read/total timeout that fires while streaming the response body is reported as `is_decode()` only — `is_timeout()` returns false, so retry logic never fires | 7 (timeout visible to caller) | `fc99bd5b15c72c65f615848d7b048df94aeadcd9` | `99996a1b3db5e7e27ce58512be42c581a9a8a7cb` | `src/error.rs` | `src/error.rs` (in-file `mod tests`) | `cargo test --lib error::tests` | ~4 min / ~1 min | First error-classification-through-a-source-chain case |
| 10 | rust | B | [BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep) | [PR #3496](https://github.com/BurntSushi/ripgrep/pull/3496) / [issue #2565](https://github.com/BurntSushi/ripgrep/issues/2565) | 2026-07-29 15:00 | **BurntSushi (owner) APPROVED**; **PR head CI 20/20 green** (post-merge nightly-toolchain failures on `main` are unrelated) | With `--max-depth`, ripgrep still parses ignore files inside directories it will never descend into — a malformed `.ignore` down there produces a spurious error | 3 (filesystem/path handling) | `dffd776a737dc19a48b758dd6a621de113794121` | `435f59fc4b43af3ab32f34d53fa34978f393fe52` | `crates/ignore/src/walk.rs` | `crates/ignore/src/walk.rs` (in-file `mod tests`) | `cargo test -p ignore --lib walk::tests` | ~3 min / ~1 min | First "don't do work you can't need" correctness contract; first depth-bounded traversal case |

### Diversity check

| Rule | Status |
|---|---|
| Exactly one Lane A + one Lane B per language | ✓ |
| Ten repositories, none in the current corpus | ✓ (verified against all 40 `case.yaml` `meta.repo`) |
| ≥6 target categories, none used >2 | ✓ **7 distinct**: 1 ×2 (pytest, poetry), 2 ×1 (cpp-httplib), 3 ×2 (libgit2, ripgrep), 4 ×1 (vite), 5 ×2 (dbal, laravel), 7 ×1 (reqwest), 8 ×1 (hono) |
| ≥3 repros spanning multiple operations | ✓ dbal (create→introspect→edit→alter→re-introspect), laravel (fake→bulk→assert), vite (update→restart→update), poetry (configure source→lock→`show --outdated`) |
| ≥3 failure/recovery or cleanup paths | ✓ reqwest (timeout mid-body), vite (restart mid-update), hono (500 → correct response), ripgrep (error suppressed for unreachable file) |
| ≥2 compatibility / default-preservation | ✓ dbal, laravel (+ cpp-httplib's encode-enabled path must stay unchanged) |
| ≥2 small production diffs (<30 lines) | ✓ libgit2 (1), dbal (4), reqwest (5), poetry (9), hono (11), ripgrep (~12) |
| ≥2 medium multi-file fixes | ✓ vite (2 files, +70/−5), laravel (2 files, +57/−2), cpp-httplib (2 files, +46/−3), pytest (4 files, +38/−10) |
| ≤2 security cases | ✓ 1 (hono CSP) |
| ≤2 parsing/encoding cases | ✓ 1 (cpp-httplib, and it is embedded in a client request workflow) |
| ≤2 cases per GitHub org | ✓ all ten orgs distinct |
| No two identical failure mechanisms | ✓ (verified pairwise: quoted-name lookup, truthy/undefined guard, header scoping, stale-object snapshot, attribute passthrough, source-reference passthrough, hook-scope inversion, inverted return code, wrapped-error recursion, depth-aware work skipping) |

**Honest caveat on categories.** libgit2 #7291 is the loosest fit. I mapped it to
category 3 because the assertion is about *path* matching (exact path vs `*.txt`
glob) against tree entries, but it could equally be called "public API
correctness at a history boundary", which is not in the list. Everything else
maps cleanly.

---

## 5. Proposed task instructions

These are the exact drafts for `case.yaml` `instruction:`. No PR numbers, SHAs,
file names, test names, or private symbols appear in any of them.

### 5.1 — libgit2 (Lane A, support ticket)

> We use libgit2 to build a "file history" view in our internal review tool. For
> each path we create a revwalk, attach a pathspec containing that one path,
> push HEAD, and list the commits that come back.
>
> On a small test repository, `git log -- README` from the command line lists two
> commits, but our walk only yields one. The commit that goes missing is always
> the repository's very first commit — the one with no parents. The same thing
> happens with a glob pathspec such as `*.txt`: we get every matching commit
> except the root one. If a path is not present in the root commit at all, the
> root commit is correctly absent, so the filter is not simply ignoring
> everything.
>
> A revwalk restricted by a pathspec should return exactly the commits `git log
> -- <path>` returns, in the same order, including root commits, and it should
> then finish normally with the usual "iteration over" status. Please fix the
> walk so the root commit is included whenever it actually contains a path
> matching the pathspec, for both literal paths and glob patterns.

### 5.2 — cpp-httplib (Lane B, acceptance story)

> **Goal.** As an integrator sending pre-encoded request targets to a strict
> RFC 3986 server, I need the client's path-encoding switch to govern the whole
> request target, so that bytes I encoded myself arrive unchanged.
>
> Today, turning path encoding off on a client only stops the path from being
> re-encoded; the query string is still decoded and re-encoded behind my back.
> That round-trip rewrites sub-delimiters and turns `%20` into `+`, which the
> server then decodes as a literal `+` rather than a space — so binary query
> payloads arrive corrupted.
>
> **Acceptance criteria**
>
> - **Given** a client with path encoding disabled, **when** I issue a GET for a
>   target whose query is already percent-encoded (for example one containing
>   `%20`, `%2C`, `%24`, `%3B`, `%00` and `%FF`), **then** the server must
>   observe the request target byte-for-byte as I supplied it, and the request
>   must complete with a 200.
> - **Given** the same client, **then** the request's parsed parameters must
>   still be populated from that query, so handlers and callers that read
>   parameters keep working.
> - **Given** a client with path encoding left at its default (enabled),
>   **when** I issue requests with paths and queries that need encoding,
>   **then** the existing encoding and normalization behaviour must be
>   completely unchanged — this must not become a global opt-out.
> - **Given** a target with no query part at all, **then** behaviour is
>   unchanged in both modes and no stray separator is appended.

### 5.3 — hono (Lane A, support ticket)

> We turn on the secure-headers middleware with both a normal Content Security
> Policy and a report-only policy, because we are trialling a stricter policy
> before enforcing it. As soon as either of the two policies uses a nonce, every
> request to the app returns a 500 instead of our page.
>
> Roughly what we configure:
>
> ```ts
> app.use('/*', secureHeaders({
>   contentSecurityPolicy: { defaultSrc: ["'self'"] },
>   contentSecurityPolicyReportOnly: { scriptSrc: ["'self'", NONCE] },
> }))
> ```
>
> With only one of the two policies configured, nonces work fine. It also breaks
> the other way round — a nonce in the enforced policy plus a plain report-only
> policy fails the same way.
>
> What we expect: each of the two CSP response headers should carry only its own
> directives, whether it is static or built with a nonce, and configuring both at
> once should never fail the request. When both policies use a nonce, they should
> both get the nonce generated for that request.

### 5.4 — vite (Lane B, acceptance story)

> **Goal.** As a developer running the dev server, I need an in-flight hot update
> to be abandoned cleanly when the server restarts underneath it, so that editing
> a file at the same moment a config or `.env` change triggers a restart does not
> take the dev server down.
>
> Right now, if a plugin's hot-update hook awaits and the server restarts during
> that await, the update keeps running against the environments that existed
> before the restart. It then crashes with a `TypeError` about setting a property
> of `undefined` while it is trying to report the original error.
>
> **Acceptance criteria**
>
> - **Given** a dev server whose plugin restarts the server from inside its
>   hot-update hook and then throws, **when** a file update is processed,
>   **then** handling that update must settle normally — no rejection and no
>   crash escaping to the caller.
> - **Given** the same restart-mid-update situation, **when** the server is
>   configured with a custom handler for dispatching hot updates to
>   environments, **then** that handler must not be invoked at all for the
>   stale update.
> - **Given** an ordinary file update with no restart, **then** hot-update
>   plugin hooks, module filtering and the resulting update dispatch must behave
>   exactly as before.
> - **Given** an update whose plugin hook throws without any restart, **then**
>   the error must still be recorded and surfaced the way it is today.
>
> Do not fix this by suppressing errors generally, and do not change the public
> shape of the hot-update hooks.

### 5.5 — doctrine/dbal (Lane A, support ticket)

> We run migrations against SQLite in our test suite. The migration reads the
> current table with the schema manager's introspection API, edits one column
> through the table editor, compares old against new, and applies the resulting
> diff.
>
> ```php
> $old = $sm->introspectTableByUnquotedName('products');
> $new = $old->edit()
>     ->modifyColumnByUnquotedName('qty', fn (ColumnEditor $e) => $e->setTypeName(Types::STRING)->setLength(32))
>     ->create();
> $sm->alterTable($sm->createComparator()->compareTables($old, $new));
> ```
>
> After that runs, the rows are all still there, but **every index and foreign
> key on the table is gone** — including a unique index on a column we never
> touched. No exception, no deprecation, nothing in the logs. If we build the
> same "old" table object by hand instead of introspecting it, the indexes and
> foreign keys survive.
>
> Altering an introspected table should preserve its indexes and foreign keys
> exactly as altering a hand-built table does, as long as the alteration does not
> change the columns they refer to.

### 5.6 — laravel/framework (Lane B, acceptance story)

> **Goal.** As an application developer writing tests, I need the fake queue to
> honour job delays during bulk dispatch the same way a real queue connection
> does, so that a test suite that passes against the fake reflects what production
> will do.
>
> Today, bulk-pushing onto the faked queue pushes every job for immediate
> processing, ignoring both the delay attribute on a job class and a delay set at
> runtime on the job instance. Real connections respect both.
>
> **Acceptance criteria**
>
> - **Given** a faked queue, **when** I bulk-push a job class that declares a
>   delay attribute together with a job that declares none, onto a named
>   connection queue, **then** exactly one of them is recorded as delayed on that
>   queue and the other is recorded as pushed immediately.
> - **Given** a faked queue, **when** I bulk-push a job instance on which I set a
>   delay at runtime, **then** it is recorded as delayed on the target queue.
> - **Given** either of the above, **then** the queue name and the payload data
>   passed to the bulk call must reach the recorded job unchanged, and the
>   existing assertions for "was this job pushed", "was it pushed on this queue"
>   and push counts must keep working for delayed jobs too.
> - **Given** a bulk push of jobs that declare no delay at all, **then**
>   behaviour is identical to today — nothing becomes delayed.

### 5.7 — pytest (Lane A, support ticket)

> Our CI runs pytest with `--no-summary` because the failure sections are very
> long and we read failures from the JUnit XML instead. After upgrading, the
> coverage report that our plugin prints at the end of the run disappeared from
> the console.
>
> We reproduced it without coverage: put this in a `conftest.py`
>
> ```python
> def pytest_terminal_summary(terminalreporter, exitstatus, config):
>     terminalreporter.write_line("MY PLUGIN SUMMARY")
> ```
>
> and run any test file with `--no-summary`. The line is never printed. Without
> `--no-summary` it is printed. Dropping `--no-summary` is not an option for us —
> we do want pytest's own failure/error sections suppressed.
>
> `--no-summary` should only suppress pytest's own summary sections. Plugins that
> implement the terminal-summary hook must still run and still be able to write
> to the terminal.

### 5.8 — poetry (Lane B, acceptance story)

> **Goal.** As a developer who gets some packages from a private index that is
> declared as an explicitly-selected source, I need `poetry show --outdated` to
> tell me when those packages have newer versions, in both the table output and
> the JSON output.
>
> Today a package pinned to a source whose priority is `explicit` is silently
> skipped by the outdated check, so it never appears as outdated even when the
> private index clearly has a newer release.
>
> **Acceptance criteria**
>
> - **Given** a project with an explicitly-selected source, a dependency pinned
>   to that source, an older version installed and locked, and a newer version
>   available only on that source, **when** I run the outdated check, **then**
>   the package is listed with its current version, the newer version, and its
>   description.
> - **Given** the same situation, **when** I ask for JSON output, **then** the
>   entry reports the same current version, latest version, description and
>   installed status.
> - **Given** the same package is declared more than once — different
>   environment markers pointing at different explicitly-selected sources —
>   **then** the latest version reported must come from the source recorded in
>   the lock file for the environment actually in use, not from whichever
>   declaration happens to come first.
> - **Given** packages that come from the default repository, or that are pinned
>   to a direct URL or VCS origin, **then** the outdated check behaves exactly as
>   it does today.

### 5.9 — reqwest (Lane A, support ticket)

> We stream large responses and set a read timeout on the client. When the
> server stalls halfway through the body, our request does fail — but the error
> we get back says `error decoding response body`, and `is_timeout()` on it
> returns `false`. Because our retry layer keys off `is_timeout()`, these
> failures are never retried and get logged as data corruption instead.
>
> The underlying cause really is the timeout: if we shorten the timeout, the same
> error appears sooner; if we remove it, the request completes.
>
> We would like `is_timeout()` to return `true` for a timeout that fires while
> the response body is being read, no matter how deep it is wrapped. It is fine
> and arguably correct that this is still classified as a decode error — the
> failure did happen while decoding the body — so please keep `is_decode()`
> returning `true` for it. A genuine decode failure with no timeout involved must
> of course still not be reported as a timeout.

### 5.10 — ripgrep (Lane B, acceptance story)

> **Goal.** As someone searching a large tree with a depth limit, I do not want
> ripgrep to be affected by ignore files sitting in directories it is never going
> to look inside.
>
> We hit this on a repository that has a generated, syntactically broken
> `.ignore` file deep in a build output directory. Searching with a depth limit
> that stops above it still reports an error about that file, and the walk spends
> time reading ignore files whose rules cannot apply to anything it will visit.
>
> **Acceptance criteria**
>
> - **Given** a directory at the configured maximum depth that contains a
>   malformed ignore file, **when** the tree is walked, **then** the entry for
>   that directory must carry no error, and the set of paths yielded must be
>   exactly what it is without the malformed file present.
> - **Given** the same walk, **then** ignore files in directories the walk does
>   descend into must keep taking effect exactly as before, at every depth up to
>   the limit.
> - **Given** a directory that is skipped for any other reason, **then** its
>   ignore files must likewise not influence the results, and the walk must still
>   traverse and terminate normally.
> - **Given** no depth limit at all, **then** every ignore file in the tree is
>   still read and applied, and malformed ones are still reported as errors.

---

## 6. Derivability matrices

Read every hidden assertion. Classification key: **D** = directly stated,
**I** = necessarily implied by the stated public contract, **P** = pre-existing
documented behaviour the prompt says to preserve.

### 6.1 libgit2 #7291 — `tests/libgit2/revwalk/pathspec.c` (new)
| Hidden assertion | Prompt sentence making it derivable | Class |
|---|---|---|
| Literal pathspec `README` yields exactly 2 commits, in `git log` order | "should return exactly the commits `git log -- <path>` returns, in the same order" | D |
| The second of those is the root commit | "The commit that goes missing is always the repository's very first commit — the one with no parents" | D |
| Glob pathspec `*.txt` yields exactly 5 commits, in `git log` order | "The same thing happens with a glob pathspec such as `*.txt` … for both literal paths and glob patterns" | D |
| The walk ends with the iteration-over status, not an error | "should then finish normally with the usual 'iteration over' status" | D |
| Root commits that do **not** contain a matching path are still excluded | "If a path is not present in the root commit at all, the root commit is correctly absent" | D |
| The specific commit OIDs asserted | Properties of the checked-in fixture repository, not of the fix — any implementation that matches `git log` produces them | I |
**Verdict: derivable.** No assertion names an internal symbol; the fix is
free-form (the gold happens to be a corrected return-code test).

### 6.2 cpp-httplib #2479 — `test/test.cc`
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Server sees request target identical to the string passed to the client | AC 1: "the server must observe the request target byte-for-byte as I supplied it" | D |
| Response status is 200 | AC 1: "the request must complete with a 200" | D |
| Pre-encoded octets `%20 %2C %24 %3B %00 %FF` survive | AC 1 enumerates exactly these | D |
| Request parameters still parsed from the query | AC 2 | D |
| Existing `PathUrlEncodeTest` cases (encoding enabled) still pass | AC 3: "existing encoding and normalization behaviour must be completely unchanged" | P |
| No `?` appended when the query is empty | AC 4 | D |
**Verdict: derivable.** `set_path_encode` is documented public API, so naming the
switch is legitimate. No maintainer-private name is required.

### 6.3 hono #5147 — `src/middleware/secure-headers/index.test.ts`
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Status 200 (not 500) with both policies configured | "configuring both at once should never fail the request" | D |
| `Content-Security-Policy` == `default-src 'self'` when only report-only has a nonce | "each of the two CSP response headers should carry only its own directives" | I |
| `Content-Security-Policy-Report-Only` matches `script-src 'self' 'nonce-…'` | same sentence, mirrored; the config in the ticket names these directives | I |
| Mirror case (nonce in enforced, static report-only) behaves symmetrically | "It also breaks the other way round — a nonce in the enforced policy plus a plain report-only policy" | D |
| When both use a nonce, the **same** nonce value appears in both headers | "When both policies use a nonce, they should both get the nonce generated for that request" | D |
| Nonce is base64-shaped | Existing documented nonce format, unchanged by this task | P |
| The header names `Content-Security-Policy` / `-Report-Only` | Public wire format — permitted to be stated | D |
**Verdict: derivable.**

### 6.4 vite #22992 — `packages/vite/src/node/server/__tests__/hmr.spec.ts` (new)
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Handling the update resolves to `undefined` (does not reject) when the hook restarts and throws | AC 1: "handling that update must settle normally — no rejection and no crash escaping to the caller" | D |
| Custom environment-dispatch handler call count is exactly 0 | AC 2: "that handler must not be invoked at all for the stale update" | D |
| Normal (no-restart) updates still run hooks and dispatch | AC 3 | P |
| A throwing hook without a restart still records the error | AC 4 | P |
| Test drives the update entry point directly | Test-harness mechanics, not an assertion about implementation | I |
**Verdict: derivable.** The prompt deliberately does not say *how* to detect
staleness (snapshot comparison, generation counter, abort token all pass).

### 6.5 doctrine/dbal #7392 — `tests/Functional/Schema/SchemaManagerFunctionalTestCase.php`
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Unique index on the untouched column survives the alter | "including a unique index on a column we never touched" | D |
| Plain index on the FK column survives | "should preserve its indexes and foreign keys" | D |
| Foreign key constraints after the alter equal those before it | same sentence | D |
| The introspected table had exactly 1 FK before the alter (guard) | Setup invariant of the scenario in the ticket | I |
| Hand-built tables keep working identically | "If we build the same 'old' table object by hand … the indexes and foreign keys survive" — stated as existing behaviour to preserve | P |
| Runs only under SQLite in our harness | Environment fact (harness pins the driver), not an assertion | — |
**Verdict: derivable.** The ticket contains the full reproduction; the fix
(quoted vs unquoted column-name lookup) is not named.

### 6.6 laravel/framework #60916 — `tests/Support/SupportTestingQueueFakeTest.php`
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Delayed size on the target queue == 1 after bulk of one delayed + one plain job | AC 1: "exactly one of them is recorded as delayed on that queue" | D |
| Both jobs assert as pushed on the named queue | AC 1 + AC 3 | D |
| Payload data reaches the recorded job unchanged | AC 3: "the payload data passed to the bulk call must reach the recorded job unchanged" | D |
| Runtime `->delay(30)` on an instance also lands in the delayed set | AC 2 | D |
| A delay attribute on the job class is honoured | AC 1: "a job class that declares a delay attribute" | D |
| Jobs with no delay keep pushing immediately | AC 4 | D |
| Names of the public delay attribute / assertion helpers | Documented public API surface — permitted | D |
**Verdict: derivable.**

### 6.7 pytest #14730 — `testing/test_terminal.py`
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| A conftest-defined terminal-summary hook writes its line under `--no-summary` | "Plugins that implement the terminal-summary hook must still run and still be able to write to the terminal", plus the exact conftest in the ticket | D |
| `= FAILURES =` section is still absent under `--no-summary` | "we do want pytest's own failure/error sections suppressed" | D |
| Pre-existing `test_no_summary` (FAILURES suppressed) still passes | Same sentence — regression guard | P |
| Marker text is chosen by the test | The ticket supplies the conftest verbatim; any correct fix prints whatever the plugin writes | I |
**Verdict: derivable.** This is the cleanest matrix in the batch — the user's own
reproduction *is* the test.

### 6.8 poetry #10982 — `tests/console/commands/test_show.py`
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Table output lists the package with current + latest version + description | AC 1 | D |
| JSON output carries name, version, latest_version, description, installed_status | AC 2 ("current version, latest version, description and installed status") | D |
| With two marker-differentiated explicit sources, latest comes from the **locked** source | AC 3, stated explicitly | D |
| The version on the *other* explicit source must not win | AC 3: "not from whichever declaration happens to come first" | I |
| Default-repository and direct-origin packages unchanged | AC 4 | P |
| Column layout / JSON key names | Existing documented output format of the command | P |
**Verdict: derivable.** The boundary scenario (AC 3) is what stops a shallow
"just always pass the first dependency's source" fix, and it is stated outright.

### 6.9 reqwest #3064 — `src/error.rs` in-file tests
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| A body-timeout wrapped as a decode error reports `is_timeout() == true` | "We would like `is_timeout()` to return `true` for a timeout that fires while the response body is being read, no matter how deep it is wrapped" | D |
| The same error still reports `is_decode() == true` | "please keep `is_decode()` returning `true` for it" | D |
| A plain I/O decode error reports `is_timeout() == false` | "A genuine decode failure with no timeout involved must of course still not be reported as a timeout" | D |
| Pre-existing `is_timeout` / `is_*` classification tests still pass | Implied: only the wrapped-timeout case changes | P |
| Tests construct errors via crate-private constructors | Test mechanics; every assertion is on public predicates | I |
**Verdict: derivable.** `is_timeout` / `is_decode` are public API and may be named.

### 6.10 ripgrep #3496 — `crates/ignore/src/walk.rs` in-file tests
| Hidden assertion | Prompt sentence/scenario | Class |
|---|---|---|
| Entry for the max-depth directory has no error despite a malformed ignore file inside it | AC 1: "the entry for that directory must carry no error" | D |
| Yielded path set is unchanged by the malformed file's presence | AC 1: "exactly what it is without the malformed file present" | D |
| All pre-existing walk tests (ignore precedence at every depth, skipping, min-depth, symlinks, …) still pass | AC 2 + AC 3 + AC 4, which restate them as behaviour to preserve | P |
| Traversal still terminates and emits the directory-exit bookkeeping | AC 3: "the walk must still traverse and terminate normally" | I |
**Verdict: derivable.** Note the whole in-file test module is grafted at
validation, so the "preserve everything else" clauses are load-bearing and are
stated in AC 2–4.

---

## 7. Harness plans

Common pattern (per `AGENTS.md` §4): `setup.sh` does `git init` + `git fetch
--depth 1 origin BASE_SHA` + `git remote remove origin`, then full dependency
prep and a warm build; `validate.sh` re-adds the remote, fetches `GOLD_SHA` at
verify time, checks out **only** the hidden test paths, and runs the selective
command.

| # | Case dir | `setup.sh` strategy | `quality.sh` | `validate.sh` command | Gold test paths to overwrite | Production paths from first-parent diff | Docker change | Runtime / risk |
|---|---|---|---|---|---|---|---|---|
| 1 | `cases/dev/cpp/libgit2_revwalk_pathspec_root` | fetch base; `cmake -S . -B build -G Ninja -DBUILD_TESTS=ON -DUSE_SSH=OFF -DUSE_HTTPS=OFF`; warm `cmake --build build` | `cmake --build build --target libgit2package -j` | re-run `cmake --build build --target libgit2_tests` then `./build/libgit2_tests -srevwalk::pathspec` | `tests/libgit2/revwalk/pathspec.c` | `src/libgit2/revwalk.c` | none (cmake+ninja present) | ~4 min setup. **Risk:** clar generates its suite index at configure time, so `validate.sh` must re-run `cmake` after dropping in the new test file. Verify no bundled deps need network. |
| 2 | `cases/dev/cpp/cpphttplib_query_verbatim` | fetch base; `cmake -S . -B build -DHTTPLIB_TEST=ON -DHTTPLIB_REQUIRE_OPENSSL=OFF -DHTTPLIB_COMPILE=ON`; warm-build `httplib-test` | `cmake --build build --target httplib -j` | `cmake --build build --target httplib-test` then `cd build/test && ./httplib-test --gtest_filter='PathUrlEncodeTest.*'` | `test/test.cc` | `httplib.h` | **`libcurl4-openssl-dev`** — `test/CMakeLists.txt` does `find_package(CURL REQUIRED)` | ~5 min setup (single large TU). **Confirmed while writing the case:** target is `httplib-test` (hyphen) and it must run from `build/test`, where CMake copies its fixture files. GTest is resolved at CONFIGURE time via `FetchContent` from `googletest/archive/main.tar.gz` when not installed system-wide — configuring in `setup.sh` keeps `validate.sh` offline. Loopback-only. |
| 3 | `cases/dev/js/hono_csp_dual_policy` | fetch base; `npm ci` (or `npm install --no-audit --fund=false`) | `npx tsc --noEmit -p tsconfig.json` | `npx vitest run src/middleware/secure-headers/index.test.ts` | `src/middleware/secure-headers/index.test.ts` | `src/middleware/secure-headers/secure-headers.ts` | none (node 22) | ~2 min. Low risk; hono's vitest config runs plain Node, no browser. |
| 4 | `cases/dev/js/vite_hmr_restart_stale` | fetch base; `corepack enable && pnpm install --frozen-lockfile` | `pnpm --filter vite exec tsc --noEmit` | `pnpm --filter vite exec vitest run src/node/server/__tests__/hmr.spec.ts` | `packages/vite/src/node/server/__tests__/hmr.spec.ts` | `packages/vite/src/node/server/hmr.ts` | needs `corepack`/pnpm — one line, stable | ~6 min setup, ~1 GB. **Highest harness risk in the batch:** monorepo install cost, and `createServer` may want `packages/vite/dist/client` even in middleware mode. Must be executed before shipping; if it needs a build step, either add `pnpm --filter vite build` to setup or fall back to the alternate. |
| 5 | `cases/dev/php/dbal_sqlite_alter_preserves_constraints` | fetch base; `composer install --no-interaction --no-progress` | `php -l` sweep over `src/` | `vendor/bin/phpunit tests/Functional/Schema/SQLiteSchemaManagerTest.php` | `tests/Functional/Schema/SchemaManagerFunctionalTestCase.php` | `src/Platforms/SQLitePlatform.php` | none (php-cli, php-sqlite3, composer present) | ~3 min. Low risk — `phpunit.xml.dist` states "By default, the tests are run against SQLite"; verified at base. Hidden path is the abstract base case, whose only delta at this commit is the new method. |
| 6 | `cases/dev/php/laravel_queuefake_bulk_delay` | fetch base; `composer install --no-interaction --no-progress` | `php -l` over changed sources, or `vendor/bin/phpunit --list-tests` smoke | `vendor/bin/phpunit tests/Support/SupportTestingQueueFakeTest.php` | `tests/Support/SupportTestingQueueFakeTest.php` | `src/Illuminate/Support/Testing/Fakes/QueueFake.php` | none | ~4 min setup (laravel/framework has a wide dev dependency set). **Risk:** confirm the suite runs without a Redis/DB service for this file — the test uses the fake only, so it should. |
| 7 | `cases/dev/python/pytest_no_summary_hook_scope` | fetch base; `pip install -e .` into `/opt/venv` | `python -m compileall -q src/_pytest` | `pytest testing/test_terminal.py -k "no_summary"` | `testing/test_terminal.py` | `src/_pytest/terminal.py` | none | ~2 min. Lowest risk in the batch. Note pytest-testing-pytest: `pytester` spawns in-process runs, fully offline. |
| 8 | `cases/dev/python/poetry_show_outdated_explicit_source` | fetch base; `pip install -e .` + `pip install -r` dev group (poetry uses `poetry` itself; simplest is `pip install -e . && pip install pytest pytest-mock deepdiff httpretty` per its dev group) | `python -m compileall -q src/poetry` | `pytest tests/console/commands/test_show.py -k outdated` | `tests/console/commands/test_show.py` | `src/poetry/console/commands/show.py` | none | ~3 min. **Risk:** poetry's dev dependencies are declared for poetry itself; the pip-based install list must be pinned carefully, and the test module must import without the full dev group. Needs execution. |
| 9 | `cases/dev/rust/reqwest_body_timeout_classification` | fetch base; `cargo test --lib --no-run -q` to warm | `cargo check --lib -q` | graft gold's `mod tests` onto the agent's `src/error.rs` (same awk pattern as `uuid_parse_panic`), then `cargo test --lib error::tests` | `src/error.rs` (test module only) | `src/error.rs` (non-test region) | none | ~4 min warm build (hyper/tokio/rustls). Medium disk. Same-file graft is a proven pattern in this repo. |
| 10 | `cases/dev/rust/ripgrep_maxdepth_ignore_skip` | fetch base; `cargo test -p ignore --lib --no-run -q` | `cargo check -p ignore -q` | graft gold's `mod tests` onto the agent's `crates/ignore/src/walk.rs`, then `cargo test -p ignore --lib walk::tests` | `crates/ignore/src/walk.rs` (test module only) | `crates/ignore/src/walk.rs` (non-test region) | none | ~3 min. Low risk; `ignore` is a small leaf crate. |

### Base/gold feasibility audit status (be honest about evidence level)

| # | Base is true pre-change state | Gold test absent at base | Fail-at-base expected reason | Evidence level |
|---|---|---|---|---|
| 1 | ✓ first parent of merge commit `9e1c61e…` | ✓ **verified** — `tests/libgit2/revwalk/` at base contains only `basic.c hidecb.c mergebase.c signatureparsing.c simplify.c`; `git_revwalk_pathspec` **is** already declared in `include/git2/revwalk.h` at base | new suite asserts 2 and 5 commits; base yields one fewer each (root dropped) | **inspected + API-checked** |
| 2 | ✓ single-parent squash | test lives inside existing `test/test.cc` | new `PreEncodedQueryNotReencoded` asserts raw target; base re-encodes | inspected |
| 3 | ✓ single-parent squash | test appended to existing spec file | new "combined modes" describe block 500s at base | inspected |
| 4 | ✓ single-parent squash | ✓ file is **new** at gold | base throws `TypeError` / invokes the custom handler | inspected |
| 5 | ✓ first parent of merge commit `34b6299…` | method appended to existing abstract test case | indexes/FKs absent after alter at base | inspected; **sqlite default verified in `phpunit.xml.dist` at base** |
| 6 | ✓ single-parent squash | methods + stubs appended to existing test file | `delayedSize('redis')` is 0 at base | inspected |
| 7 | ✓ single-parent squash | method appended inside existing class | marker line absent at base | inspected |
| 8 | ✓ single-parent squash | two new test functions appended | latest version not found → package not listed at base | inspected |
| 9 | ✓ single-parent squash | tests inside `src/error.rs` `mod tests` | `is_timeout()` false at base | inspected |
| 10 | ✓ single-parent squash | test inside `crates/ignore/src/walk.rs` `mod tests` | `entry.error()` is `Some(..)` at base | inspected |

**No case in this batch has had both legs executed.** Every row above is
*inspected* or *command-checked*, never *fully executed*. `scripts/verify_case.sh`
must run before any of these ship.

### Leak-hygiene notes specific to this batch
- **#4 (vite)** — `pnpm install` writes a lockfile-derived store and `node_modules/.vite`; confirm the snapshot excludes them and that no `.git` remote survives.
- **#5, #6 (composer)** — `composer install` writes `composer.lock` metadata and a `vendor/` tree; the existing PHP cases already handle this, reuse their pattern.
- **#2 (cpp-httplib)** — if gtest is fetched by CMake at configure time, it must be warmed in `setup.sh` so `validate.sh` needs no network.
- **#1 (libgit2)** — the clar suite index is generated; make sure the generated index is regenerated at validate time and that the generated file does not reveal the test name to the agent during the run.
- All ten: `git fetch --depth 1 origin <BASE_SHA>` keeps gold out of the object store until `validate.sh`.

---

## 8. Alternates and rejection reasons

Two or more per language, with the concrete reason each lost.

### C / C++
| Alternate | Reason it lost |
|---|---|
| ninja-build/ninja [#2680](https://github.com/ninja-build/ninja/pull/2680) | **Too large.** +647/−212 with a 444-line rewrite of `graph.cc`. Best review record in the whole scan (62 review comments; `digit-google` and `mathstuf` both requested changes and had them resolved) and a superb public workflow (build → touch → rebuild), but fail-to-pass would rest on a deep multi-concept change. Reconsider if a large-diff slot is ever wanted. |
| yhirose/cpp-httplib [#2504](https://github.com/yhirose/cpp-httplib/pull/2504) | **Flaky timing risk.** "Skip request body drain when connection will close" is a better category fit (7/12) but the reproduction involves a client that keeps producing chunks while the server decides to close — timing-sensitive. |
| libgit2 [#7322](https://github.com/libgit2/libgit2/pull/7322) | **Thinner coverage.** `is_shallow` via commondir maps more cleanly to category 3/12 and is a nice worktree lifecycle, but only 24 lines of test versus #7291's 105-line standalone suite. |
| libuv [#5206](https://github.com/libuv/libuv/pull/5206) | **Bot-assisted authorship.** The author discloses "I used Codex to help investigate, implement, and test this change." Reference solution is partly model-generated — disqualifying for a contamination-controlled benchmark. |
| CLIUtils/CLI11 [#1384](https://github.com/CLIUtils/CLI11/pull/1384) | **Not human-authored, no review.** PR body opens with ":robot: _AI text below_ :robot:"; self-merged with zero reviews. |
| google/googletest [#5041](https://github.com/google/googletest/pull/5041), [#5039](https://github.com/google/googletest/pull/5039) | **No tests.** Production-only diffs. |

### JavaScript / TypeScript
| Alternate | Reason it lost |
|---|---|
| expressjs/express [#7366](https://github.com/expressjs/express/pull/7366) | **Possible silent skip.** Two approvals and a lovely 304/QUERY contract, but the gold tests call `this.skip()` when `shouldSkipQuery(process.versions.node)` is true. If the image's Node 22 lacks QUERY support the test skips → passes at base → no fail-to-pass. Promote only after checking the Node floor. |
| honojs/hono [#5164](https://github.com/honojs/hono/pull/5164) | **Same repo already used**, and the production delta is 8 lines of relaxed name validation — good compat story, thin edit. |
| sindresorhus/execa [#1256](https://github.com/sindresorhus/execa/pull/1256) | **No independent review.** Authored and merged by the sole maintainer; process-lifecycle surface is excellent otherwise. |
| prettier/prettier [#19725](https://github.com/prettier/prettier/pull/19725) | **Snapshot-based assertions.** Idempotency is the ideal category-6 fill, but assertions live in `__snapshots__` files, which graft badly and leak formatting output. |

### PHP
| Alternate | Reason it lost |
|---|---|
| laravel/framework [#60877](https://github.com/laravel/framework/pull/60877) | **Derivability leak (hard reject).** The `schedule:list` timezone converter's data provider pins ~40 maintainer-chosen normalization policies — which fields collapse to `*` vs `a-b/s` vs a comma list, when rows merge vs split, that February and `L` are deliberately left unconverted, that `0 1 31 * *` becomes `0 16 30 1,3,5,7,8,10,12 *`. Stating these in a prompt is dictating the algorithm; not stating them makes the case unpassable. |
| laravel/framework [#60907](https://github.com/laravel/framework/pull/60907) | **Backport.** Merged to `12.x`, a maintenance branch; the `13.x` original is #60893. Good failure-path case (deprecation logging must never fatal) if a backport is acceptable. |
| doctrine/dbal [#7484](https://github.com/doctrine/dbal/pull/7484) | **Same repository** as the selected case; cannot reuse in this batch. |
| api-platform/core [#8348](https://github.com/api-platform/core/pull/8348) | **Too large + config leak.** 22 files, and it introduces a new maintainer-named configuration key that the prompt would have to name. |
| pytest-style note: sebastianbergmann/phpunit | **Bot-only window.** Every July merge is renovate[bot]. |

### Python
| Alternate | Reason it lost |
|---|---|
| pytest-dev/pytest [#14331](https://github.com/pytest-dev/pytest/pull/14331) | **Derivability leak (hard reject).** Best public story in the Python scan (temp-dir cleanup fails on directories with the execute bit stripped; two core approvals; 160 lines of new tests) — but the hidden test does `from _pytest.pathlib import _chmod_rwx`, a private helper *introduced by the gold patch*. No prompt can make that name derivable. |
| pytest-dev/pytest [#14692](https://github.com/pytest-dev/pytest/pull/14692) | **Backup for slot 7.** "Allow int for `truncation_limit_lines`/`truncation_limit_chars` in TOML" — authored by core maintainer Pierre-Sassoulas, and it is a genuine two-config-representation (ini vs TOML) case. Lost only because #14730's surface is crisper. |
| psf/black [#5211](https://github.com/psf/black/pull/5211) | **No review approvals.** `BLACK_NUM_WORKERS` validation is an ideal env-var/exit-code case (+17 prod / +20 test) but carries zero reviews. |
| pypa/pip [#14204](https://github.com/pypa/pip/pull/14204) | **No real test coverage.** 5 files changed; the only test delta is `+1/−1`. Zero reviews. |
| psf/black [#5192](https://github.com/psf/black/pull/5192) | **Too trivial.** Adding `EOFError` to an `except` tuple. |

### Rust
| Alternate | Reason it lost |
|---|---|
| clap-rs/clap [#6409](https://github.com/clap-rs/clap/pull/6409) | **No tests.** 18 review comments from epage (outstanding review evidence) and a great env/shell-detection surface, but the diff touches production source only. |
| BurntSushi/ripgrep [#3475](https://github.com/BurntSushi/ripgrep/pull/3475) | **Same repository** as the selected case. |
| seanmonstar/reqwest [#3065](https://github.com/seanmonstar/reqwest/pull/3065) | **Same repository**; also a pure feature addition (`http1_max_headers`) with a weaker failure story. |
| astral-sh/uv [#20839](https://github.com/astral-sh/uv/pull/20839) | **Bot-heavy repo + build cost.** Conflicting-flag diagnostics is a clean CLI exit-status case, but a large share of uv's July merges come from `astral-automations-bot[bot]`, and the build is expensive. |
| astral-sh/ruff | **Mechanical-sweep window.** Late July is dominated by "Remove unused APIs from …" refactors and vendored-typeshed bot syncs. |

---

## 9. Recommendation and stop gate

Ranked by expected benchmark value (contract clarity × investigation depth ×
harness safety):

| Rank | Case | Why |
|---|---|---|
| 1 | **poetry #10982** (py, B) | Newest PR in the batch (merged the morning of mining), maintainer-approved, and its second scenario — marker-differentiated sources where the *locked* source must win — is a purpose-built trap for a shallow fix. Cheapest fail-to-pass to verify. |
| 2 | **doctrine/dbal #7392** (php, A) | The single best support ticket: the PR body *is* the reproduction. 4-line production fix behind a genuinely non-obvious cause (quoted vs unquoted column names), offline on SQLite, lead-maintainer reviewed. |
| 3 | **pytest #14730** (py, A) | Perfect derivability — the user's conftest reproduction is literally the hidden test. Fastest case in the batch. |
| 4 | **hono #5147** (js, A) | Pure black-box HTTP: configure two headers, observe status and both header values. Zero internals in any assertion. |
| 5 | **ripgrep #3496** (rust, B) | Rare "don't do work you can't need" correctness contract; the grafted test module drags in ripgrep's full existing walk suite, so a special-case fix cannot survive. |
| 6 | **reqwest #3064** (rust, A) | Crisp public predicate contract (`is_timeout` ∧ `is_decode`) with a real user report behind it. Small, but the source-chain recursion is a real insight. |
| 7 | **libgit2 #7291** (cpp, A) | Strongest test coverage relative to diff size (105 new lines against a 1-token fix) and the repro is "compare to `git log`". Production edit is thin. |
| 8 | **cpp-httplib #2479** (cpp, B) | Clean config→wire contract with a boundary the prompt states outright. Repo has the batch's thinnest formal review trail (single maintainer). |
| 9 | **laravel #60916** (php, B) | Excellent fake-vs-real parity story, but zero GitHub review records — Laravel merges by maintainer push, so "real review" rests on CI plus maintainer acceptance only. |
| 10 | **vite #22992** (js, B) | Best *scenario* in the batch (restart mid-update) and two core-maintainer approvals, but the heaviest and least certain harness: pnpm monorepo install, possible build prerequisite. |

### Flags carried forward (nothing here is hidden)

1. **No case has executed fail-to-pass.** All base/gold evidence is *inspected* or
   *command-checked*. `scripts/verify_case.sh` on all ten is the first
   implementation step.
2. **#10 vite** is the one case whose harness could fail outright. If
   `pnpm --filter vite exec vitest run …` needs a prior `pnpm build`, either
   absorb that into `setup.sh` or fall back to express #7366 (after confirming
   Node 22 supports the QUERY method so the gold tests do not silently skip).
3. **#9 laravel** has no GitHub review record. If the "real review" bar must be
   evidenced by an approving reviewer, swap it for another PHP repo — but note
   that Laravel's *process* is maintainer-push, so absence of reviews is not
   evidence of low scrutiny.
4. **#8 cpp-httplib** review depth is single-maintainer. Accepted on adoption and
   CI (26/26 green) rather than on review breadth.
5. **#7 pytest author provenance.** #14730's author (`l46983284-cpu`) also
   appears filing small changes across ripgrep and black in the same window — a
   pattern consistent with AI-assisted contribution. It was approved by core
   maintainer nicoddemus under a CONTRIBUTING policy that explicitly bans
   unsupervised agentic contributions and requires `Co-authored-by` disclosure,
   and no such trailer is present. If you want zero doubt here, swap in
   pytest #14692 (authored by core maintainer Pierre-Sassoulas; ini-vs-TOML
   config typing).
6. **Undocumented cutoffs.** `gpt-5.6-sol`, `glm-5.2`, `gemini-3.5-flash`,
   `minimax-m3`, `kimi-k2.6` and `deepseek-4-pro` have no cutoff I could verify
   from an authoritative source. The 30-day window is the mitigation, not a proof.

### Stop gate

**Stopping here for approval, as instructed.** No case directories created, no
`docker/Dockerfile.agent` changes, no `cases/_specs/` writes. Nothing is
implemented until you say so.
