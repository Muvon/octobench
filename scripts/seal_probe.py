"""Prove the scored phase reaches model endpoints and nothing else.

setup and validation are intentionally unsealed. During the agent invocation,
default-deny egress prevents solution retrieval through source hosts, search,
mirrors, package registries, or unknown future domains.
"""
import os
import sys

os.environ["OCTOBENCH_SEAL_NETWORK"] = "1"
os.environ.pop("OCTOBENCH_ALLOW_HOSTS", None)

from pathlib import Path  # noqa: E402
from cli.main import seal_network, unseal_network  # noqa: E402
from runners.executor import DockerExecutor  # noqa: E402

ws = Path("/tmp/seal-probe-ws")
ws.mkdir(parents=True, exist_ok=True)
ex = DockerExecutor(
    image="octobench-agent:latest",
    workspace=ws,
    case_dir=Path("cases/dev/longrun/js/fastify"),
    octomind_config=Path("configs/octomind/octomind.toml"),
    container_name="seal-probe",
)


MODEL_ENDPOINTS = (
    "https://token-plan.ap-southeast-1.maas.aliyuncs.com",
    "https://auth.openai.com",
    "https://api.openai.com",
    "https://openrouter.ai",
)

NON_MODEL_ENDPOINTS = (
    "https://github.com",
    "https://raw.githubusercontent.com",
    "https://www.google.com/search?q=octobench",
    "https://search.brave.com/search?q=octobench",
    "https://grep.app/search?q=octobench",
    "https://registry.npmjs.org",
    "https://pypi.org",
    "https://crates.io",
    "https://repo.packagist.org",
)


def request(url):
    result = ex.run([
        "curl", "-sS", "-L", "--max-time", "8", "-o", "/dev/null",
        "-w", "%{http_code}", url,
    ])
    code = (result.stdout or "").strip()
    return result.exit_code == 0 and code not in {"", "000"}, code or "FAILED"


def probe(label, expected):
    failures = []
    for url, should_reach in expected:
        reached, code = request(url)
        print(f"  {label:8} {url:62} -> {code}")
        if reached != should_reach:
            failures.append(f"{url}: reached={reached}, expected={should_reach}")
    if failures:
        raise RuntimeError("; ".join(failures))


try:
    print("before seal:")
    probe("open", [(url, True) for url in MODEL_ENDPOINTS + NON_MODEL_ENDPOINTS])
    print(seal_network(ex) or "", end="")
    print("after seal:")
    probe(
        "sealed",
        [(url, True) for url in MODEL_ENDPOINTS]
        + [(url, False) for url in NON_MODEL_ENDPOINTS],
    )
    unseal_network(ex)
    print("after unseal:")
    probe("open", [(url, True) for url in MODEL_ENDPOINTS + NON_MODEL_ENDPOINTS])
finally:
    ex.close()
