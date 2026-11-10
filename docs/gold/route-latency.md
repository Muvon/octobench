# ChatGPT plan inference: Octomind's route vs Codex's route (per-request latency)

Octomind and Codex both run `gpt-6.1-sol` on a ChatGPT plan login, but each sends its requests to a
different endpoint. Measured on 60 paired single requests, a request through Octomind's route takes
about 1.11× as long as the same request through Codex's route (median of per-pair ratios, bootstrap
95% CI 1.05–1.23). For prompts of 20K–90K input tokens the ratio is 1.15× (CI 1.05–1.29); for a
prompt of about 10K tokens there is no measurable difference (1.01×, CI 0.83–1.18). Octomind is
slower even though its requests carried about 5.7K fewer input tokens than Codex's.

Use this when reading GOLD time results: part of Octomind's per-call wall time is the route, not the
client.

Measured 2026-11-07, 09:55–10:12 UTC, on the benchmark box (`dev`, x86_64), while a paired gap6 run
was in progress (both clients were affected by that load equally, see Method). Raw samples:
[`route-latency.samples.tsv`](route-latency.samples.tsv).

## The two routes

| | Codex (first-party) | Octomind via octolib (third-party) |
|---|---|---|
| Endpoint | `https://chatgpt.com/backend-api/codex` (built into the Codex CLI) | `https://api.openai.com/v1/responses` (`octolib/src/llm/providers/chatgpt/websocket.rs:29`) |
| Transport used | Codex default | WebSocket (`request_transport = "websocket"`, Octomind's bench default) |
| Credential | ChatGPT login (`~/.codex/auth.json`) | ChatGPT login (OAuth, octolib `chatgpt` provider) |
| Allowed for third parties | no | yes, the documented route |

OpenAI's Sign in with ChatGPT documentation for open-source clients prescribes the third-party route
and forbids the other one: send the OAuth access token to `POST https://api.openai.com/v1/responses`
and "do not point it at ChatGPT's `backend-api` endpoints"
([Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)).
Octolib uses the route it is required to use, so this gap cannot be closed in Octomind.

## Method

- Bench image `octobench-agent:gold24`; each client runs in its own container exactly as the bench
  starts it, with its own login mounted. The test never reads the auth files.
- Model `gpt-6.1-sol`, reasoning effort `low` for both (Octomind `-c model.reasoning_effort=low`,
  Codex `-c model_reasoning_effort="low"`).
- Each client keeps its normal system prompt and tools; only the user message is controlled.
- One prompt text, "Reply with the single word OK and nothing else.", preceded by 0, ~20K, ~40K or
  ~80K tokens of source code (`octomind/src/session/chat/session/core.rs`, repeated). Every run makes
  exactly one model request; runs with any other request count are discarded (none were).
- 15 rounds. Each round runs every (client, size) combination once, in a freshly shuffled order, so
  both routes are sampled under the same load and minutes. Every run is a fresh process with a fresh
  connection, for both clients.
- Request time:
  - Octomind: the session's `total_api_time_ms`, which octolib measures around the whole
    `chat_completion` call: token handling, connection, sending and the complete response
    (`octolib/src/llm/providers/chatgpt/mod.rs:94-103`).
  - Codex: the rollout's `task_started` event to its `token_count` event (millisecond timestamps).
- Input tokens: as each provider reported them (Octomind input plus cached input; Codex
  `last_token_usage.input_tokens`).
- Statistics: per size, the median of the 15 per-round ratios (Octomind ÷ Codex) and a bootstrap 95%
  CI of that median (5,000 resamples, seed 7). Overhead counts as real only when the CI excludes 1.0.
- Scripts: `/tmp/probe-net/run2.sh` and `/tmp/probe-net/summary.py` on `dev`.

## Result

| added prompt | n | Octomind median | Codex median | Octomind input | Codex input | Octomind ÷ Codex | 95% CI |
|---|---|---|---|---|---|---|---|
| none | 15 | 3,165 ms | 3,245 ms | 8.2K | 14.1K | 1.01 | 0.83–1.18 |
| ~20K | 15 | 3,805 ms | 2,887 ms | 27.8K | 33.5K | 1.29 | 1.12–1.59 |
| ~40K | 15 | 3,826 ms | 3,323 ms | 47.4K | 53.1K | 1.07 | 1.01–1.26 |
| ~80K | 15 | 4,123 ms | 3,477 ms | 86.8K | 92.5K | 1.09 | 1.05–1.43 |
| all sizes | 60 | | | | | 1.11 (geomean 1.12) | 1.05–1.23 |
| 20K–90K | 45 | | | | | 1.15 (geomean 1.15) | 1.05–1.29 |

Remeasured 2026-11-10 with octomind 0.70.1 and codex-cli 0.167.0. Raw samples:
[`route-latency.2026-11-10.samples.tsv`](route-latency.2026-11-10.samples.tsv).

| added prompt | n | Octomind median | Codex median | Octomind input | Codex input | Octomind ÷ Codex | 95% CI |
|---|---|---|---|---|---|---|---|
| none | 15 | 3,462 ms | 2,978 ms | 7.9K | 14.5K | 1.20 | 0.93–1.35 |
| ~20K | 15 | 3,524 ms | 2,878 ms | 27.6K | 33.9K | 1.24 | 0.90–1.77 |
| ~40K | 15 | 3,397 ms | 3,273 ms | 47.1K | 53.5K | 1.05 | 0.96–1.57 |
| ~80K | 15 | 3,819 ms | 3,522 ms | 86.5K | 92.9K | 1.10 | 0.89–1.38 |
| all sizes | 60 | | | | | 1.14 (geomean 1.15) | 0.98–1.24 |
| 20K–90K | 45 | | | | | 1.10 (geomean 1.15) | 0.96–1.23 |

Every confidence interval here includes 1.0, so by the rule above this run does not
establish the gap on its own; the point estimates stay at 1.10–1.15.

## What this does and does not show

- It shows a per-request cost of Octomind's route against Codex's for the same model, effort and
  user message: about +11% overall and +15% once the prompt is 20K tokens or more, with fewer input
  tokens on Octomind's side.
- It does not separate the endpoint from the transport: Octomind's HTTP transport could not be
  measured, because every HTTP request failed with `Malformed ChatGPT response … expected value at
  line 1 column 1` (an octolib bug, recorded separately).
- Both clients ran cold (new process and connection per run). Within a real session both reuse their
  connection, so the absolute times there are lower; the comparison here is like for like.
- An earlier version of this test (2026-10-27) ran Octomind at reasoning effort medium and Codex at
  low, and reported about +1.8 s per request. That result was invalid and is replaced by this one.
