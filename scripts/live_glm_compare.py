"""Live per-case comparison of glm-octomind (final) vs glm-opencode (in flight).

Opencode's invocation-level results.json lands only at set completion, so its
completed cases are reconstructed from the run log + per-case logs.
"""
import glob
import json
import os
import re

ROOT = "/home/box/work/muvon/octobench"
GLM_IN, GLM_OUT = 1.40, 4.40

octo = {}
for f in glob.glob(f"{ROOT}/results-full-octomind/2*/results.json"):
    for r in json.load(open(f))["results"]:
        s = r["scoring"]
        octo[r["case_id"]] = (
            "FAIL" if s["validation_failed"] else "PASS",
            r["judge"].get("score"),
            r.get("cost_usd") or 0,
            r["result"]["elapsed_ms"] // 60000,
        )

log = open("/tmp/full-opencode.log", errors="replace").read()
completed = re.findall(r"completed case=(\S+)", log)
vals, cur = {}, None
for line in log.splitlines():
    m = re.search(r"\[octobench\] case=(\S+)", line)
    if m and "completed" not in line:
        cur = m.group(1)
    m = re.search(r"script=validate\.sh end exit=(\d+)", line)
    if m and cur:
        vals[cur] = "PASS" if m.group(1) == "0" else "FAIL"

print(f"{'case':44s} | {'glm-OCTOMIND':22s} | glm-OPENCODE")
tot_o = tot_c = 0.0
wins_j = 0
for cid in completed:
    dirs = sorted(glob.glob(f"{ROOT}/results-full-opencode/2*/{cid}/opencode__glm-5.2/logs"))
    judge, cost = "?", 0.0
    if dirs:
        d = dirs[-1]
        try:
            raw = open(os.path.join(d, "judge.raw.log"), errors="replace").read()
            m = re.search(r"\"score\"[: ]+(\d+)", raw)
            judge = m.group(1) if m else "?"
        except Exception:
            pass
        i = o = 0
        try:
            for ln in open(os.path.join(d, "provider.raw.jsonl"), errors="replace"):
                if "step_finish" in ln:
                    try:
                        t = json.loads(ln)["part"]["tokens"]
                        i += t["input"]
                        o += t["output"]
                    except Exception:
                        pass
        except Exception:
            pass
        cost = (i * GLM_IN + o * GLM_OUT) / 1e6
    ov, oj, oc, om = octo.get(cid, ("?", "?", 0, 0))
    tot_o += oc
    tot_c += cost
    left = f"{ov} j={oj} ${oc:.2f} {om}m"
    right = f"{vals.get(cid, '?')} j={judge} ${cost:.2f}"
    print(f"{cid:44s} | {left:22s} | {right}")
print(f"{'TOTAL over opencode-completed cases':44s} | ${tot_o:.2f}".ljust(70)
      + f" | ${tot_c:.2f}")
