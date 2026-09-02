"""Fail if any agent trace used a tool the clean bench forbids.

The bench compares clients on a shared prompt with upstream unreachable. A client
that reaches the web — its own server-side search, a fetch tool, or a knowledge
tool that takes a URL — is answering from the merged fix, not from the repository.
Cross-case memory is forbidden for the same reason: it carries state between cases.

This is a post-hoc check on the recorded traces, so it catches a misconfiguration
the env-var gate in cli/main.py cannot: a client whose tool surface came from
somewhere other than octobench (a tap agent, a provider default, a stale config).

Usage:
  .venv/bin/python scripts/audit_tools.py <results-dir> [...]
Exit 1 if any forbidden tool call is found.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# Anything that can reach outside the container, plus persistent memory.
FORBIDDEN = {
    "brave_web_search", "websearch", "web_search", "webfetch", "web_fetch",
    "WebSearch", "WebFetch", "knowledge", "fetch",
    "memorize", "remember", "memory", "memory-read", "memory-write",
}

# Not forbidden, but not part of any client's bench surface either: seeing these
# means the agent tag resolved to something wider than the configured role.
# `monitor` is deliberately absent: the developer role grants it (and only it)
# from the orchestration server, because it is how a long command reports
# completion instead of being polled for. `tap` and `schedule` remain unlisted
# in the role, so seeing them still means the surface widened.
SUSPECT = {"schedule", "agent", "task"}


def tools_in(trace: Path) -> Counter:
    found = Counter()
    for line in trace.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except Exception:
            continue
        # octomind
        if event.get("type") == "tool_use" and event.get("tool"):
            found[event["tool"]] += 1
        # opencode
        part = event.get("part") or {}
        if part.get("tool"):
            found[part["tool"]] += 1
        # codex: server-side tools are typed items, and its web_search runs on
        # OpenAI's infrastructure — the container network seal never sees it.
        item = event.get("item") or {}
        if item.get("type") in {"web_search", "web_fetch"}:
            found[f"codex:{item['type']}"] += 1
    return found


def main() -> None:
    roots = [Path(a) for a in sys.argv[1:]]
    if not roots:
        raise SystemExit("usage: audit_tools.py <results-dir> [...]")

    violations: list[tuple[str, str, dict]] = []
    suspects: list[tuple[str, str, dict]] = []
    traces = 0
    for root in roots:
        # _stream_*.jsonl covers claude, which has no provider.raw.jsonl events
        # in the shapes tools_in() parses — the /git-cache check still applies.
        for trace in sorted(set(root.rglob("provider.raw.jsonl"))
                            | set(root.rglob("_stream_*.jsonl"))):
            traces += 1
            found = tools_in(trace)
            case = trace.parts[-4] if len(trace.parts) >= 4 else trace.name
            bad = {k: v for k, v in found.items()
                   if k in FORBIDDEN or k.startswith("codex:")}
            # The git-mirror mount (runners/executor.py) is harness-only
            # territory: it holds the upstream repos' FULL history, including
            # the gold commits. An agent that touches it read the answer key.
            if "/git-cache" in trace.read_text(errors="replace"):
                bad["git-cache-access"] = 1
            odd = {k: v for k, v in found.items() if k in SUSPECT}
            if bad:
                violations.append((str(root), case, bad))
            elif odd:
                suspects.append((str(root), case, odd))

    for root, case, odd in suspects:
        print(f"SUSPECT {root} {case}: {odd}")
    for root, case, bad in violations:
        print(f"FORBIDDEN {root} {case}: {bad}")

    print(f"audited {traces} trace(s): "
          f"{len(violations)} forbidden, {len(suspects)} suspect")
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
