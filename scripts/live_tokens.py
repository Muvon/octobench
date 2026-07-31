"""Per-completed-case token detail for the live round-2 runs."""
import glob
import json
import os

ROOT = "/home/box/work/muvon/octobench"


def claude_row(path):
    last = None
    for ln in open(path, errors="replace"):
        if "total_cost_usd" in ln:
            last = ln
    if not last:
        return None
    o = json.loads(last)
    u = o.get("usage", {})
    return (u.get("input_tokens", 0), u.get("cache_creation_input_tokens", 0),
            u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0),
            o.get("total_cost_usd", 0), o.get("num_turns"))


def octomind_row(path):
    last = None
    for ln in open(path, errors="replace"):
        if '"type":"cost"' in ln or '"type": "cost"' in ln:
            last = ln
    if not last:
        return None
    o = json.loads(last)
    return (o.get("input_tokens", 0), 0,
            o.get("cache_read_tokens") or o.get("cached_tokens") or 0,
            o.get("output_tokens", 0), None, None)


def main():
    for prov, sub, fn in (("OPUS", "claude", claude_row), ("GLM", "octomind", octomind_row)):
        for d in sorted(glob.glob(f"{ROOT}/results-cases2-{sub}/*/dev2_*/")):
            cid = d.rstrip("/").split("/")[-1].replace("dev2_", "")
            pf = glob.glob(os.path.join(d, "*", "logs", "provider.raw.jsonl"))
            if not pf:
                continue
            row = fn(pf[0])
            if not row:
                continue
            inp, cw, cr, out, cost, turns = row
            cost_s = f"${cost:.2f}" if cost is not None else "-"
            turns_s = f"turns={turns}" if turns else ""
            print(f"{prov:4s} {cid:38s} in={inp:>7,} cache_w={cw:>8,} "
                  f"cache_r={cr:>11,} out={out:>7,} {cost_s} {turns_s}")


if __name__ == "__main__":
    main()
