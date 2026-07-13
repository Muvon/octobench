#!/usr/bin/env python3
"""tau2-bench solo-mode bridge (runs inside the benchmark container).

Exposes the tau2 telecom environment to a shell CLI agent (octomind/codex/claude)
so it can solve a solo-mode ticket WITHOUT a user simulator, then scores the run
with tau2's own evaluator so numbers are faithful to the upstream benchmark.

Subcommands (agent-facing):
  init   <task_id>                 write ticket.md + policy.md + tools.json; reset log
  init_index <n>                   same, selecting the n-th task of the split (no shell
                                   quoting of the bracketed task ids — used by setup_cmds)
  tools                            print the JSON tool schemas (also in tools.json)
  call   <tool> '<json-args>'      execute one assistant tool call; print its result
  reward                           (verify step) print TAU2_REWARD=<0..1> for the log

State is a per-workspace append-only call log (TAU2_STATE, default calls.jsonl).
Each `call`/`reward` rebuilds a fresh solo env and replays the log — telecom solo
trajectories are short, so the O(n^2) replay is negligible.
# ponytail: O(n^2) log replay per call; switch to a persisted env snapshot only if
# a domain ever needs long trajectories.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

# tau2/litellm/loguru print banners to stdout at import time; redirect those to
# stderr so this bridge's stdout stays clean, machine-readable output for the agent.
os.environ.setdefault("LITELLM_LOG", "CRITICAL")
with contextlib.redirect_stdout(sys.stderr):
    from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
    from tau2.data_model.simulation import SimulationRun, TerminationReason
    from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
    from tau2.registry import registry

    with contextlib.suppress(Exception):
        from loguru import logger

        logger.remove()  # silence loguru's default stderr sink too

DOMAIN = os.environ.get("TAU2_DOMAIN", "telecom")
SPLIT = os.environ.get("TAU2_SPLIT", "small")  # 20-task solo split (matches the config)
STATE = Path(os.environ.get("TAU2_STATE", "calls.jsonl"))
TASK_FILE = Path(os.environ.get("TAU2_TASK", "task.json"))


def _tasks():
    return registry.get_tasks_loader(DOMAIN)(SPLIT)


def _task_by_id(task_id: str):
    for t in _tasks():
        if t.id == task_id:
            return t
    raise SystemExit(f"tau2_bridge: task id not found in domain {DOMAIN}: {task_id}")


def _fresh_env():
    return registry.get_env_constructor(DOMAIN)(solo_mode=True)


def _load_log():
    if not STATE.exists():
        return []
    return [json.loads(x) for x in STATE.read_text().splitlines() if x.strip()]


def _replay(env, log):
    """Apply every prior assistant tool call to a fresh env, in order."""
    for i, entry in enumerate(log):
        env.get_response(
            ToolCall(id=f"c{i}", name=entry["name"], arguments=entry["arguments"],
                     requestor="assistant")
        )


def _trajectory(log):
    """Reconstruct the half-duplex message trajectory tau2's evaluator expects."""
    msgs = []
    for i, entry in enumerate(log):
        cid = f"c{i}"
        tc = ToolCall(id=cid, name=entry["name"], arguments=entry["arguments"],
                      requestor="assistant")
        msgs.append(AssistantMessage(role="assistant", content=None, tool_calls=[tc]))
        msgs.append(ToolMessage(id=cid, role="tool", content=entry.get("result", ""),
                                requestor="assistant", error=bool(entry.get("error"))))
    return msgs


def cmd_init(task_id: str) -> None:
    task = _task_by_id(task_id)
    TASK_FILE.write_text(task.model_dump_json())
    STATE.write_text("")
    env = _fresh_env()
    Path("ticket.md").write_text(task.ticket or "")
    Path("policy.md").write_text(env.policy or "")
    schemas = [t.openai_schema for t in env.get_tools()]
    Path("tools.json").write_text(json.dumps(schemas, indent=2))
    print(f"tau2 solo task ready: {task_id}")
    print("Read ticket.md and policy.md. List tools with `tau2 tools`.")
    print("Call a tool: `tau2 call <tool_name> '<json args>'`. Finish: nothing to do.")


def cmd_init_index(n: str) -> None:
    tasks = _tasks()
    idx = int(n)
    if not 0 <= idx < len(tasks):
        raise SystemExit(f"tau2_bridge: index {idx} out of range (0..{len(tasks) - 1})")
    cmd_init(tasks[idx].id)


def cmd_tools() -> None:
    env = _fresh_env()
    print(json.dumps([t.openai_schema for t in env.get_tools()], indent=2))


def cmd_call(name: str, args_json: str) -> None:
    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as e:
        raise SystemExit(f"tau2_bridge: invalid JSON args: {e}")
    log = _load_log()
    env = _fresh_env()
    _replay(env, log)
    resp = env.get_response(
        ToolCall(id=f"c{len(log)}", name=name, arguments=args, requestor="assistant")
    )
    entry = {"name": name, "arguments": args, "result": resp.content or "",
             "error": bool(resp.error)}
    with STATE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(resp.content or "")


def cmd_reward() -> None:
    if not TASK_FILE.exists():
        print("TAU2_REWARD=0.0")
        print("tau2_bridge: no task.json (init not run)")
        return
    from tau2.data_model.tasks import Task

    task = Task.model_validate_json(TASK_FILE.read_text())
    sim = SimulationRun(
        id="octobench", task_id=task.id, start_time="", end_time="", duration=0.0,
        termination_reason=TerminationReason.AGENT_STOP, messages=_trajectory(_load_log()),
    )
    info = evaluate_simulation(sim, task, EvaluationType.ALL, solo_mode=True, domain=DOMAIN)
    print(f"TAU2_REWARD={float(info.reward)}")
    print(json.dumps(info.model_dump(), default=str)[:2000])


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "init":
        cmd_init(rest[0])
    elif cmd == "init_index":
        cmd_init_index(rest[0])
    elif cmd == "tools":
        cmd_tools()
    elif cmd == "call":
        cmd_call(rest[0], rest[1] if len(rest) > 1 else "")
    elif cmd == "reward":
        cmd_reward()
    else:
        raise SystemExit(f"tau2_bridge: unknown command {cmd}")


if __name__ == "__main__":
    main()
