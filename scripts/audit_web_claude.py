"""Audit a claude trace for network access (companion to audit_web.py).

Claude logs tool calls as `tool_use` blocks on assistant messages, so the check
is: which tools were used at all (WebSearch/WebFetch should be absent — the
provider passes --disallowed-tools), and did any Bash command reach the network.
"""
import glob
import json
import re
import sys

NET_CMD = re.compile(
    r"\b(curl|wget|nc|ncat|telnet|ssh|scp|rsync|ftp)\b"
    r"|\bgit\s+(fetch|clone|pull|ls-remote|remote\s+add)\b"
    r"|\b(pip|pip3|npm|pnpm|yarn|cargo|composer|go)\s+(install|add|get|update|fetch|ci)\b"
    r"|urllib|requests\.get|http\.client|socket\.create_connection",
    re.I,
)
UPSTREAM = re.compile(r"raw\.githubusercontent|github\.com|gitlab\.com|/pull/\d+", re.I)
WEB_TOOLS = {"WebSearch", "WebFetch"}

roots = sys.argv[1:] or ["results-longrun-claude-mirror"]
tools: dict[str, int] = {}
cmds = flagged = 0
for root in roots:
    for path in sorted(glob.glob(f"{root}/*/*/*/turns/*/logs/provider.raw.jsonl")):
        seq, turn = path.split("/")[2], path.split("/")[-3]
        for line in open(path, errors="replace"):
            try:
                obj = json.loads(line)
            except Exception:
                continue
            content = (obj.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                name = b.get("name") or "?"
                tools[name] = tools.get(name, 0) + 1
                inp = b.get("input") or {}
                if name in WEB_TOOLS:
                    flagged += 1
                    print(f"[WEB-TOOL {name}] {seq}/{turn}: {json.dumps(inp)[:200]}")
                    continue
                if name != "Bash":
                    continue
                cmds += 1
                cmd = inp.get("command") or ""
                hits = [
                    t for t, rx in (("NET-CMD", NET_CMD), ("UPSTREAM-IN-CMD", UPSTREAM))
                    if rx.search(cmd)
                ]
                if hits:
                    flagged += 1
                    print(f"[{','.join(hits)}] {seq}/{turn}")
                    print(f"  cmd: {' '.join(cmd.split())[:300]}")
print(f"\ntools used: {tools}")
print(f"{cmds} Bash commands audited, {flagged} flagged")
