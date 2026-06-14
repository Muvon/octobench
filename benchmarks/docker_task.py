"""DockerTaskAdapter: env-required benchmarks with a programmatic verdict.

Generalizes the SWE-bench-Live flow for any benchmark whose verdict is "run a
command in a container and check the result": CTF flag capture (Cybench/CVE-Bench),
terminal tasks (Terminal-Bench), EHR/FHIR state checks (MedAgentBench), test
execution (ResearchCodeBench), DB-state checks (LiveSQLBench), etc.

Per-instance flow inside the benchmark's Docker image:
  setup_cmds (prep/reset env) -> agent SETUP runs -> verify_cmds (check) ->
  resolved = success_regex matches (agent output + verify output) OR last verify
  cmd exits 0. Objective verdict drives the score; the judge adds a quality lens.

Each instance needs a Docker image to exist (pulled/built upstream). When the
image is missing or docker is unavailable, the run is recorded as a clean failure
with an explanatory note rather than crashing the batch.
"""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from benchmarks import hf
from benchmarks.base import (
    BenchmarkAdapter,
    Instance,
    RunContext,
    apply_provider_result,
    base_record,
    set_verdict,
)
from judges.llm_judge import run_judge
from providers.factory import get_provider
from runners.executor import DockerExecutor

from cli.main import log, safe_id, write_text


class DockerTaskAdapter(BenchmarkAdapter):
    engine = "docker_task"

    def __init__(self, config: Dict):
        super().__init__(config)
        self.image: str = self.config.get("image", "")
        self.platform: Optional[str] = self.config.get("platform")
        self.workdir: str = self.config.get("workdir", "/workspace")
        self.mount_workspace: bool = bool(self.config.get("mount_workspace", True))
        self.system_prompt: str = self.config.get(
            "system_prompt",
            "You are an autonomous agent working in a real environment. Complete the "
            "task using the available tools. When done, stop.",
        )
        self.default_split: str = self.config.get("split", "test")
        self.run_judge_flag: bool = bool(self.config.get("run_judge", True))

    def requires_docker(self) -> bool:
        return True

    # --- loading ------------------------------------------------------------

    def load_instances(self, limit=None, split=None, instance_id=None) -> List[Instance]:
        src = self.config.get("source", "inline")
        if src == "inline":
            rows = self.config.get("instances", [])
            insts = [self._inst(i, r) for i, r in enumerate(rows)]
        elif src == "hf":
            split = split or self.default_split
            n = limit or int(self.config.get("default_limit", 10))
            rows = hf.fetch_n(
                self.config["dataset"], split, n, config=self.config.get("hf_config", "default")
            )
            insts = [self._inst_hf(i, r) for i, r in enumerate(rows)]
        else:
            raise RuntimeError(f"docker_task: unknown source '{src}'")
        if instance_id:
            insts = [x for x in insts if x.id == instance_id]
        if limit:
            insts = insts[:limit]
        return insts

    def _inst(self, idx: int, r: Dict) -> Instance:
        return Instance(
            id=str(r.get("id", f"{self.name}-{idx}")),
            prompt=str(r.get("prompt", r.get("problem", ""))),
            system_prompt=r.get("system_prompt", ""),
            meta={
                "domain": self.domain,
                "image": r.get("image", self.image),
                "platform": r.get("platform", self.platform),
                "workdir": r.get("workdir", self.workdir),
                "setup_cmds": r.get("setup_cmds", []),
                "verify_cmds": r.get("verify_cmds", []),
                "success_regex": r.get("success_regex"),
                "success_exit": r.get("success_exit", False),
            },
            raw=r,
        )

    def _inst_hf(self, idx: int, r: Dict) -> Instance:
        f = self.config.get("fields", {})
        g = lambda k, d=None: hf.get_field(r, f.get(k), d)  # noqa: E731
        return Instance(
            id=str(g("id", None) or f"{self.name}-{idx}"),
            prompt=str(g("prompt", "") or ""),
            meta={
                "domain": self.domain,
                "image": str(g("image", self.image) or self.image),
                "platform": self.platform,
                "workdir": self.workdir,
                "setup_cmds": g("setup_cmds", []) or [],
                "verify_cmds": g("verify_cmds", []) or [],
                "success_regex": self.config.get("success_regex"),
                "success_exit": self.config.get("success_exit", False),
            },
            raw=r,
        )

    # --- running ------------------------------------------------------------

    def run_instance(self, instance, target, ctx: RunContext, out_dir: Path) -> Dict:
        provider = target["provider"]
        m = instance.meta
        image = m.get("image") or self.image
        workdir = m.get("workdir") or self.workdir
        logs = out_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        ws = out_dir / "workspace"
        if ws.exists():
            shutil.rmtree(ws)
        ws.mkdir(parents=True, exist_ok=True)

        record = base_record(instance, target, ctx, self.name)

        if not image:
            return self._fail(record, ctx, "no image configured for this benchmark")

        name = f"obd-{safe_id(instance.id)[:20]}-{provider[:6]}-{int(time.time() * 1000)}"
        executor = DockerExecutor(
            image,
            ws,
            ws,
            ctx.repo_config,
            name,
            workdir=workdir,
            platform=m.get("platform"),
            mount_workspace=self.mount_workspace,
            mount_case=False,
        )
        try:
            # setup
            for cmd in m.get("setup_cmds", []):
                self._sh(executor, cmd)

            prompt = (
                f"System:\n{instance.system_prompt or self.system_prompt}\n\n"
                f"Instruction:\n{instance.prompt}\n"
            )
            session = name
            pr = get_provider(provider).run_task(
                prompt=prompt,
                workdir=workdir,
                provider_model=target["provider_model"],
                session_name=session,
                executor=executor,
            )
            write_text(logs / "provider.stdout.log", pr.stdout or "")
            write_text(logs / "provider.stderr.log", pr.stderr or "")
            write_text(logs / "provider.raw.jsonl", pr.raw_output or "")

            # verify
            verify_out = ""
            last_rc = 0
            for cmd in m.get("verify_cmds", []):
                r = self._sh(executor, cmd)
                verify_out += f"$ {cmd}\n{r.stdout}\n{r.stderr}\n"
                last_rc = r.exit_code
            write_text(logs / "verify.log", verify_out)

            resolved = self._resolve(m, pr.stdout or "", verify_out, last_rc)
            pricing = ctx.models_cfg.get("models", {}).get(target["benchmark_model"], {}).get(
                "pricing"
            )
            apply_provider_result(record, pr, pricing)
            gate = (
                "OBJECTIVE GATE (authoritative, source of truth):\n"
                f"resolved={resolved}\n(last_verify_exit={last_rc})\n"
                "The environment check determines correctness; judge solution quality."
            )
            set_verdict(record, resolved, "docker_task", {"last_verify_exit": last_rc})

            if self.run_judge_flag:
                provider_ev = get_provider(provider).build_provider_evidence(pr)
                evidence = (
                    f"<verify_output>\n{verify_out[:6000]}\n</verify_output>\n"
                    f"<provider_evidence>\n{provider_ev}\n</provider_evidence>"
                )
                judge_meta = dict(ctx.judge_cfg)
                judge_meta["io_dir"] = str(logs.resolve())
                judge_meta["repo_root"] = str(ctx.repo_root)
                record["judge"] = run_judge(
                    {
                        "task": prompt,
                        "prep_log": "",
                        "quality_log": "",
                        "validation_log": gate,
                        "evidence_log": evidence,
                    },
                    judge_meta,
                    str(ctx.repo_root),
                )
                write_text(logs / "judge.raw.log", str(record["judge"].get("_judge_raw", "")))
        except RuntimeError as e:
            return self._fail(record, ctx, f"docker env error: {e}")
        finally:
            executor.close()

        log(
            f"[bench] {self.name} {instance.id} {provider} "
            f"resolved={record['verdict']['objective']}",
            ctx.verbosity,
            "normal",
        )
        return record

    # --- internals ----------------------------------------------------------

    def _sh(self, executor: DockerExecutor, script: str):
        return executor.run(["bash", "-lc", script])

    def _resolve(self, m: Dict, agent_out: str, verify_out: str, last_rc: int) -> bool:
        rx = m.get("success_regex")
        if rx:
            haystack = (agent_out or "") + "\n" + (verify_out or "")
            return bool(re.search(rx, haystack, re.M | re.I))
        if m.get("success_exit"):
            return last_rc == 0
        # Default: last verify command succeeding is the signal.
        return last_rc == 0

    def _fail(self, record: Dict, ctx: RunContext, note: str) -> Dict:
        record["result"] = {"stdout": "", "stderr": note, "exit_code": 1, "elapsed_ms": 0}
        set_verdict(record, False, "docker_task", {"error": note})
        record["judge"] = {"score": 0, "reasoning": note, "issues": [note], "confidence": 0.0}
        log(f"[bench] {self.name} SKIPPED: {note}", ctx.verbosity, "normal")
        return record
