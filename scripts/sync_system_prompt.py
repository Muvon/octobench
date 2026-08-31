"""Push configs/common/system_prompt.md into every harness config, or verify sync.

The clean bench compares clients, not prompts, so all four agents must receive
byte-identical instructions. Octomind and opencode need the text embedded in
their config files; claude and codex receive it as a CLI argument read straight
from the canonical file at run time, so they cannot drift.

Usage:
  .venv/bin/python scripts/sync_system_prompt.py          # write
  .venv/bin/python scripts/sync_system_prompt.py --check  # verify, exit 1 on drift
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "configs" / "common" / "system_prompt.md"
OCTOMIND = ROOT / "configs" / "octomind" / "octomind.toml"
OPENCODE = ROOT / "configs" / "opencode" / "opencode.json"

# The `developer` role's system block, from `system = """` to the closing `"""`.
OCTOMIND_RE = re.compile(
    r'(name = "developer"\n(?:[^\n]*\n)*?system = """\n)([\s\S]*?)(\n""")'
)


def octomind_current(text: str) -> str:
    m = OCTOMIND_RE.search(text)
    if not m:
        raise SystemExit("octomind.toml: no `developer` role with a system block")
    return m.group(2)


def main() -> None:
    check = "--check" in sys.argv
    prompt = CANONICAL.read_text().rstrip("\n")

    toml_text = OCTOMIND.read_text()
    oc_cfg = json.loads(OPENCODE.read_text())
    oc_prompt = oc_cfg.get("agent", {}).get("build", {}).get("prompt")

    drift = []
    if octomind_current(toml_text) != prompt:
        drift.append("octomind.toml developer role")
    if oc_prompt != prompt:
        drift.append("opencode.json agent.build.prompt")

    if check:
        if drift:
            print("SYSTEM PROMPT DRIFT: " + ", ".join(drift))
            raise SystemExit(1)
        print(f"system prompt in sync across all harnesses ({len(prompt)} chars)")
        return

    if drift:
        OCTOMIND.write_text(OCTOMIND_RE.sub(lambda m: m.group(1) + prompt + m.group(3), toml_text))
        oc_cfg.setdefault("agent", {}).setdefault("build", {})["prompt"] = prompt
        OPENCODE.write_text(json.dumps(oc_cfg, indent=2) + "\n")
    print(f"synced ({len(prompt)} chars): " + (", ".join(drift) if drift else "already in sync"))


if __name__ == "__main__":
    main()
