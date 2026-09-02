"""Post-hoc efficiency scorecard: who solves, at what token/time/dollar price.

Usage:
  .venv/bin/python scripts/gold_scorecard.py [--suite=gold] \
      'claude=results-gold-oneshot-*/*/results.json results-gold-longrun-*/*/results.json' \
      'codex-sol=...'

Reads EXISTING oneshot and longrun records (no benchmark execution). Unit of
analysis is one oneshot case or one longrun TURN ("item"). Prints one markdown
table to stdout: metric rows × client columns.

Project stats rules: medians for cost/time/tokens, MEAN for judge (median
judge score inverts client ranking), totals where a total is the message.
"""
from __future__ import annotations

import glob
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _tok(t: dict) -> tuple[int, int, int, int]:
    """(non-cache, cache_read, output, reasoning) from a tokens block."""
    t = t or {}
    inp = t.get("input") or 0
    out = t.get("output") or 0
    reas = t.get("reasoning") or 0
    return inp + out + reas, t.get("cached_input") or 0, out, reas


def _steps_in(logs_dir_glob: str, base: Path) -> int:
    """Tool-call count from whatever trace format the client left behind.
    provider.raw.jsonl: octomind (tool_use), codex (item.started), opencode
    (part.tool). Claude leaves stream-json `_stream_*.jsonl` files instead
    (one per session resume), with tool_use nested in assistant messages."""
    traces = list(base.glob(f"{logs_dir_glob}/provider.raw.jsonl")) or list(
        base.glob(f"{logs_dir_glob}/_stream_*.jsonl")
    )
    if not traces:
        return 0
    steps = 0
    for trace in traces:
        for line in trace.read_text(errors="replace").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") == "tool_use":
                steps += 1
            elif obj.get("type") == "item.started":
                if (obj.get("item") or {}).get("type") in {
                    "command_execution", "file_change", "mcp_tool_call", "web_search", "todo_list",
                }:
                    steps += 1
            elif obj.get("type") == "assistant":
                for block in ((obj.get("message") or {}).get("content") or []):
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        steps += 1
            part = obj.get("part") or {}
            if part.get("tool"):
                steps += 1
    return steps + 1


def _case_steps(result_path: Path, record: dict) -> int:
    # Records merged in by rerun_failed.py keep their logs under reruns/<ts>/,
    # not beside this results.json; the record's workdir points at the truth.
    wd = record.get("workdir")
    if wd and Path(wd).parent.is_dir():
        return _steps_in("logs", Path(wd).parent)
    return _steps_in(f"{record['case_id']}/*/logs", result_path.parent)


def _turn_steps(result_path: Path, sequence_id: str, turn_no: int) -> int:
    return _steps_in(f"{sequence_id}/*/turns/turn_{turn_no}/logs", result_path.parent)


def load_items(pattern: str, suite: tuple[set, set] | None) -> list[dict]:
    """Flatten oneshot cases and longrun turns from all matching results.json."""
    items: list[dict] = []
    for path in [p for g in pattern.split() for p in sorted(glob.glob(g))]:
        try:
            data = json.loads(open(path).read())
        except Exception:
            continue
        for r in data.get("results", []):
            if "case_id" in r:  # oneshot
                cid = r["case_id"]
                if suite and not any(cid.endswith(s) for s in suite[0]):
                    continue
                sc = r.get("scoring") or {}
                v = (r.get("scripts") or {}).get("validate") or {}
                passed = not sc.get("validation_failed", v.get("exit_code", 1) != 0)
                nc, cache, out, reas = _tok(r.get("tokens"))
                items.append({
                    "passed": passed,
                    "judge": (r.get("judge") or {}).get("score"),
                    "final": sc.get("final_score") or 0,
                    "cost": r.get("cost_usd") or 0,
                    "ms": (r.get("result") or {}).get("elapsed_ms") or 0,
                    "noncache": nc, "cache": cache, "out": out, "reas": reas,
                    "steps": _case_steps(Path(path), r),
                })
            elif "sequence_id" in r:  # longrun
                sid = r["sequence_id"]
                if suite and not any(sid.startswith(s) for s in suite[1]):
                    continue
                for t in r.get("turns") or []:
                    nc, cache, out, reas = _tok(t.get("tokens"))
                    items.append({
                        "passed": bool((t.get("validation") or {}).get("passed")),
                        "judge": (t.get("judge") or {}).get("score"),
                        "final": (t.get("scoring") or {}).get("final_score") or 0,
                        "cost": t.get("cost_usd") or 0,
                        "ms": (t.get("provider") or {}).get("elapsed_ms") or 0,
                        "noncache": nc, "cache": cache, "out": out, "reas": reas,
                        "steps": _turn_steps(Path(path), sid, t.get("turn") or 0),
                    })
    return items


def _suite_sets(name: str) -> tuple[set, set]:
    oneshot, longrun = set(), set()
    for ln in (REPO / "configs" / "suites" / f"{name}.txt").read_text().splitlines():
        ln = ln.strip()
        if ln.startswith("oneshot/"):
            lang, case = ln.split("/")[1:3]
            oneshot.add(f"_{lang}_{case}")
        elif ln.startswith("longrun/"):
            lang, repo = ln.split("/")[1:3]
            longrun.add(f"longrun_{lang}_{repo}")
    return oneshot, longrun


def _median(xs):
    return statistics.median(xs) if xs else 0


def _p90(xs):
    return sorted(xs)[int(0.9 * (len(xs) - 1))] if xs else 0


def _m(ms):  # minutes string
    return f"{ms / 60000:.1f}m"


def _k(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K"


def column(items: list[dict]) -> dict[str, str]:
    n = len(items)
    if not n:
        return {}
    solved = [i for i in items if i["passed"]]
    failed = [i for i in items if not i["passed"]]
    p = len(solved)
    cost = sum(i["cost"] for i in items)
    nc_total = sum(i["noncache"] for i in items)
    judges = [i["judge"] for i in items if i["judge"] is not None]
    reas_t, out_t = sum(i["reas"] for i in items), sum(i["out"] for i in items)
    with_steps = [i for i in items if i["steps"] > 1]
    ms = [i["ms"] for i in items]
    return {
        "items solved": f"**{p}/{n}** ({100 * p / n:.0f}%)",
        "judge mean": f"{statistics.mean(judges):.1f}" if judges else "-",
        "Σ final score": f"{sum(i['final'] for i in items):.0f}",
        "cost total": f"${cost:.2f}",
        "$ per solve": f"${cost / p:.3f}" if p else "-",
        "cost waste %": f"{100 * sum(i['cost'] for i in failed) / cost:.1f}%" if cost else "-",
        "tok median/item": _k(_median([i["noncache"] for i in items])),
        "tok per solve": _k(nc_total / p) if p else "-",
        "tok waste %": (
            f"{100 * sum(i['noncache'] for i in failed) / nc_total:.1f}%" if nc_total else "-"
        ),
        "cache read median": _k(_median([i["cache"] for i in items])),
        "reasoning share": f"{100 * reas_t / (reas_t + out_t):.0f}%" if reas_t else "n/a",
        "time median": _m(_median(ms)),
        "time p90": _m(_p90(ms)),
        "time max": _m(max(ms)),
        "agent hours": f"{sum(ms) / 3.6e6:.1f}h",
        "steps median": (f"{_median([i['steps'] for i in with_steps]):.0f}"
                         f" ({len(with_steps)}/{n} traced)") if with_steps else "no traces",
    }


def main() -> None:
    suite = None
    cols: list[tuple[str, list[dict]]] = []
    for arg in sys.argv[1:]:
        if arg.startswith("--suite="):
            suite = _suite_sets(arg.split("=", 1)[1])
            continue
        label, _, pattern = arg.partition("=")
        cols.append((label, pattern))
    if not cols:
        raise SystemExit(__doc__)
    table = [(label, column(load_items(pattern, suite))) for label, pattern in cols]
    metrics = next((list(c.keys()) for _l, c in table if c), [])
    if not metrics:
        raise SystemExit("no records matched")
    print("| metric | " + " | ".join(lbl for lbl, _c in table) + " |")
    print("|---" * (len(table) + 1) + "|")
    for m in metrics:
        print(f"| {m} | " + " | ".join(c.get(m, "-") for _l, c in table) + " |")
    print("\n_Item = one oneshot case or one longrun turn. Medians for cost/time/"
          "tokens; judge is a MEAN (median judge inverts ranking). Reasoning "
          "share is n/a for providers that fold thinking into output tokens. "
          "Steps come from provider.raw.jsonl traces; coverage shown per column._")


if __name__ == "__main__":
    main()
