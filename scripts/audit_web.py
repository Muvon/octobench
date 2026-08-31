"""Audit Codex/OpenCode traces for network and hidden-case access.

The seal is the enforcement boundary; this is the post-run evidence check. It
reports network-capable commands, web tools, hidden `/case` reads, and upstream
references from raw provider traces.
"""
import glob
import json
import re
import sys

NET_CMD = re.compile(
    r"\b(curl|wget|nc|ncat|telnet|ssh|scp|rsync|ftp)\b"
    r"|\bgit\s+(fetch|clone|pull|ls-remote|remote\s+add)\b"
    r"|\b(pip|pip3|npm|pnpm|yarn|cargo|composer|go)\s+(install|add|get|update|fetch|ci)\b"
    r"|urllib|requests\.get|http\.client|socket\.create_connection|fetch\(",
    re.I,
)
UPSTREAM = re.compile(
    r"raw\.githubusercontent|github\.com|gitlab\.com|bitbucket\.org|"
    r"/pull/\d+|/commit/[0-9a-f]{7,}",
    re.I,
)
SEARCH = re.compile(
    r"\b(websearch|web_search|search_query)\b|"
    r"(?:google|bing|duckduckgo)\.[a-z.]+/search|search\.brave\.com|"
    r"grep\.app|sourcegraph\.com",
    re.I,
)
HIDDEN = re.compile(r"(?<![A-Za-z0-9_.-])/(?:case|cases)(?:/|\b)|\$CASE_DIR|\bCASE_DIR=", re.I)

roots = sys.argv[1:] or ["results-longrun-codex-sol"]
total = flagged = 0
for root in roots:
    for path in sorted(glob.glob(f"{root}/**/provider.raw.jsonl", recursive=True)):
        parts = path.split("/")
        seq = next((p for p in parts if p.startswith("longrun_")), parts[-6] if len(parts) >= 6 else "?")
        turn = parts[-3] if len(parts) >= 3 else "?"
        for line in open(path, errors="replace"):
            try:
                obj = json.loads(line)
            except Exception:
                continue
            typ = obj.get("type")
            item = obj.get("item") or {}
            cmd = out = ""
            web_tool = ""
            if typ == "item.completed" and item.get("type") == "command_execution":
                cmd = item.get("command") or ""
                out = item.get("aggregated_output") or ""
            elif typ == "tool_use":
                part = obj.get("part") or {}
                tool = str(part.get("tool") or "")
                inputs = ((part.get("state") or {}).get("input") or {})
                if tool in {"webfetch", "websearch"}:
                    web_tool = tool
                if tool in {"bash", "shell"}:
                    cmd = str(inputs.get("command") or "")
            else:
                continue
            total += 1
            hits = []
            if web_tool:
                hits.append(f"WEB-TOOL:{web_tool}")
            if NET_CMD.search(cmd):
                hits.append("NET-CMD")
            if SEARCH.search(cmd):
                hits.append("SEARCH-IN-CMD")
            if UPSTREAM.search(cmd):
                hits.append("UPSTREAM-IN-CMD")
            if HIDDEN.search(cmd):
                hits.append("HIDDEN-IN-CMD")
            if UPSTREAM.search(out):
                hits.append("UPSTREAM-IN-OUTPUT")
            if hits:
                flagged += 1
                print(f"[{','.join(hits)}] {seq}/{turn}")
                print(f"  cmd: {' '.join(cmd.split())[:300]}")
                if "UPSTREAM-IN-OUTPUT" in hits:
                    m = UPSTREAM.search(out)
                    s = max(0, m.start() - 120)
                    print(f"  out: ...{' '.join(out[s:m.end() + 120].split())}...")
print(f"\n{total} shell commands audited, {flagged} flagged")
raise SystemExit(1 if flagged else 0)
