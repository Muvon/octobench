"""Live status table for a pair of parallel case runs (claude vs octomind).

Parses the two run logs plus per-case judge/provider logs that appear as each
case completes; costs come from provider.raw.jsonl (claude reports
total_cost_usd; octomind cost events carry tokens, priced at glm-5.2 rates).
"""
import glob
import json
import os
import re
from datetime import datetime

GLM_IN, GLM_CACHED, GLM_OUT = 1.40, 0.26, 4.40  # $/1M, ollama glm-5.2

ROOT = "/home/box/work/muvon/octobench"


def parse_run(log_path, results_glob):
    cases, order, cur = {}, [], None
    if not os.path.exists(log_path):
        return cases, order
    for line in open(log_path, errors="replace"):
        m = re.match(r"\[(\S+)\] \[octobench\] case=(\S+)", line)
        if m and "completed" not in line:
            cur = m.group(2)
            if cur not in cases:
                cases[cur] = {"start": m.group(1), "val": None, "judge": None,
                              "cost": None, "end": None}
                order.append(cur)
        m = re.search(r"script=validate\.sh end exit=(\d+)", line)
        if m and cur:
            cases[cur]["val"] = "PASS" if m.group(1) == "0" else "FAIL"
        m = re.search(r"\[(\S+)\] \[octobench\] completed case=(\S+)", line)
        if m:
            cases[m.group(2)]["end"] = m.group(1)

    for d in glob.glob(results_glob):
        cid = d.rstrip("/").split("/")[-2]
        if cid not in cases:
            continue
        jf = os.path.join(d, "logs", "judge.raw.log")
        if os.path.exists(jf):
            mm = re.search(r"\"score\"[: ]+(\d+)", open(jf, errors="replace").read())
            if mm:
                cases[cid]["judge"] = int(mm.group(1))
        pf = os.path.join(d, "logs", "provider.raw.jsonl")
        if os.path.exists(pf):
            cost = None
            for ln in open(pf, errors="replace"):
                if "total_cost_usd" in ln:
                    try:
                        cost = json.loads(ln).get("total_cost_usd", cost)
                    except Exception:
                        pass
                elif '"type":"cost"' in ln or '"type": "cost"' in ln:
                    try:
                        o = json.loads(ln)
                        it, ot = o.get("input_tokens"), o.get("output_tokens")
                        ct = o.get("cache_read_tokens") or o.get("cached_tokens") or 0
                        if it is not None and ot is not None:
                            cost = ((it - ct) * GLM_IN + ct * GLM_CACHED + ot * GLM_OUT) / 1e6
                    except Exception:
                        pass
            cases[cid]["cost"] = cost
    return cases, order


def mins(start, end):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    e = datetime.strptime(end, fmt) if end else datetime.utcnow()
    return (e - datetime.strptime(start, fmt)).total_seconds() / 60


def cell(cases, cid):
    r = cases.get(cid)
    if not r:
        return "-"
    if not r["end"]:
        return f"RUN {mins(r['start'], None):.0f}m"
    v = r["val"] or "?"
    j = r["judge"] if r["judge"] is not None else "?"
    c = f"${r['cost']:.2f}" if r["cost"] else "$?"
    return f"{v} j={j} {c} {mins(r['start'], r['end']):.0f}m"


def main():
    import sys
    prefix = sys.argv[1] if len(sys.argv) > 1 else "cases2"
    c_cases, c_order = parse_run(
        f"/tmp/{prefix}-claude.log", f"{ROOT}/results-{prefix}-claude/*/dev*_*/claude__*/")
    o_cases, o_order = parse_run(
        f"/tmp/{prefix}-octomind.log", f"{ROOT}/results-{prefix}-octomind/*/dev*_*/octomind__*/")
    all_ids = c_order + [i for i in o_order if i not in c_order]

    print(f"{'case':40s} | {'OPUS':22s} | GLM")
    for cid in all_ids:
        print(f"{cid.replace('dev2_', ''):40s} | {cell(c_cases, cid):22s} | {cell(o_cases, cid)}")
    cd = sum(1 for r in c_cases.values() if r["end"])
    od = sum(1 for r in o_cases.values() if r["end"])
    cj = sum(r["judge"] or 0 for r in c_cases.values() if r["end"])
    oj = sum(r["judge"] or 0 for r in o_cases.values() if r["end"])
    cc = sum(r["cost"] or 0 for r in c_cases.values())
    oc = sum(r["cost"] or 0 for r in o_cases.values())
    cv = sum(1 for r in c_cases.values() if r["end"] and r["val"] == "PASS")
    ov = sum(1 for r in o_cases.values() if r["end"] and r["val"] == "PASS")
    print(f"{'TOTALS pass/done judgeSum cost':40s} | "
          f"{cv}/{cd} j={cj} ${cc:.2f} | {ov}/{od} j={oj} ${oc:.2f}")


if __name__ == "__main__":
    main()
