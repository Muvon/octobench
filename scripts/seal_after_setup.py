"""Locate the seal failure: probe alone seals fine, the real run does not.

Only difference is that the real run executes setup.sh first, so this walks the
same path — same executor construction, setup, guardrails, then seal — printing
the container's state at each step.
"""
import os
import sys

os.environ["OCTOBENCH_SEAL_NETWORK"] = "1"

from pathlib import Path  # noqa: E402

from cli.main import install_guardrails, run_case_script, seal_network  # noqa: E402
from runners.executor import DockerExecutor  # noqa: E402

case = Path(sys.argv[1] if len(sys.argv) > 1 else "cases/dev/longrun/cpp/ada")
ws = Path(os.environ.get("WS", "/tmp/seal-after-setup-ws"))
ws.mkdir(parents=True, exist_ok=True)
ex = DockerExecutor(
    image="octobench-agent:latest",
    workspace=ws,
    case_dir=case,
    octomind_config=Path("configs/octomind/octomind.toml"),
    container_name="seal-after-setup",
)


def state(label):
    r = ex.run(["bash", "-lc",
                "id -u; touch /etc/_probe && echo ETC-OK || echo ETC-DENIED; rm -f /etc/_probe; "
                "df -h / | tail -1"])
    print(f"[{label}] {(r.stdout or r.stderr).strip()}")


try:
    state("fresh container")
    log = run_case_script(ex, "setup.sh", "quiet")
    print(f"setup exit={log['exit_code']}")
    state("after setup.sh")
    install_guardrails(ex)
    state("after guardrails")
    seal_network(ex)
    print("SEAL OK")
finally:
    ex.close()
