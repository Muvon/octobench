"""QAAdapter: single-turn QA benchmarks.

modes:
  mcq           -> multiple-choice, objective letter match
  final_answer  -> free-form answer, objective numeric/string/set match
  constraint    -> IFEval/IFBench-style, objective programmatic constraint check
  judge_text    -> open-ended generation graded by the LLM judge against a rubric

The agent SETUP under test (claude/codex/octomind + model) runs in a fresh
workspace and is asked to write its final answer to `answer.txt`; the verdict is
computed from that (objective modes) or handed to the judge (judge_text).
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmarks import hf, verify
from benchmarks.base import (
    BenchmarkAdapter,
    Instance,
    RunContext,
    apply_provider_result,
    base_record,
    make_executor,
    set_verdict,
)
from judges.llm_judge import run_judge
from providers.factory import get_provider

# Functions reused from the main runner (no import cycle: cli.main never imports
# benchmarks).
from cli.main import log, safe_id, write_text

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

DOMAIN_SYSTEM = {
    "": "You are a careful, expert problem solver.",
    "math": "You are an expert mathematician. Reason step by step, then give the final answer.",
    "health-medical": "You are an expert clinician answering a medical question.",
    "frontier-reasoning-knowledge": "You are an expert answering a hard graduate-level question.",
    "instruction-following": "You are a helpful assistant. Follow every instruction exactly.",
    "marketing-content-creative": "You are an expert copywriter and creative writer.",
    "finance": "You are an expert financial analyst.",
    "legal": "You are an expert attorney answering a legal question.",
    "science-research-deepresearch": "You are an expert research scientist.",
}


class QAAdapter(BenchmarkAdapter):
    engine = "qa"

    def __init__(self, config: Dict):
        super().__init__(config)
        self.mode: str = self.config.get("mode", "mcq")
        self.match_mode: str = self.config.get("match", "math")
        self.run_judge_flag: bool = bool(self.config.get("run_judge", True))
        self.default_split: str = self.config.get("split", "test")

    # --- loading ------------------------------------------------------------

    def load_instances(self, limit=None, split=None, instance_id=None) -> List[Instance]:
        src = self.config.get("source", "inline")
        if src == "inline":
            rows = self.config.get("instances", [])
            insts = [self._inst_from_inline(i, r) for i, r in enumerate(rows)]
        elif src == "hf":
            split = split or self.default_split
            n = limit or int(self.config.get("default_limit", 20))
            ds = self.config["dataset"]
            cfg = self.config.get("hf_config", "default")
            rows = hf.fetch_n(ds, split, n, config=cfg)
            insts = [self._inst_from_hf(i, r) for i, r in enumerate(rows)]
        else:
            raise RuntimeError(f"qa: unknown source '{src}'")

        if instance_id:
            insts = [x for x in insts if x.id == instance_id]
        if limit:
            insts = insts[:limit]
        return insts

    def _inst_from_inline(self, idx: int, r: Dict) -> Instance:
        return Instance(
            id=str(r.get("id", f"{self.name}-{idx}")),
            prompt=str(r.get("prompt", r.get("question", ""))),
            gold=r.get("answer"),
            system_prompt=r.get("system_prompt", ""),
            reference=str(r.get("reference", "")),
            rubric=str(r.get("rubric", self.config.get("rubric", ""))),
            constraints=r.get("constraints"),
            choices=r.get("choices"),
            meta={"domain": self.domain},
            raw=r,
        )

    def _inst_from_hf(self, idx: int, r: Dict) -> Instance:
        f = self.config.get("fields", {})
        get = lambda key, default=None: hf.get_field(r, f.get(key), default)  # noqa: E731
        rid = str(get("id", None) or r.get("id") or f"{self.name}-{idx}")
        question = str(get("question", "") or "")
        choices = self._build_choices(r, f)
        gold = get("answer", None)
        constraints = None
        if self.mode == "constraint":
            constraints = self._build_constraints(r, f)
        return Instance(
            id=rid,
            prompt=question,
            gold=gold,
            system_prompt=str(get("system_prompt", "") or ""),
            reference=str(get("reference", "") or ""),
            rubric=str(get("rubric", "") or self.config.get("rubric", "")),
            constraints=constraints,
            choices=choices,
            meta={"domain": self.domain},
            raw=r,
        )

    def _build_choices(self, r: Dict, f: Dict) -> Optional[List[str]]:
        if self.mode != "mcq":
            return None
        # 1) a single field of options: a list (MMLU/MMLU-Pro/SuperGPQA) or a
        #    letter-keyed dict {"A": ..., "B": ...} (MedXpertQA).
        choices_field = f.get("choices")
        if choices_field:
            val = hf.get_field(r, choices_field)
            if isinstance(val, list):
                return [str(x) for x in val]
            if isinstance(val, dict) and val:
                return [str(v) for _k, v in sorted(val.items())]
        # 2) per-option columns, e.g. opa/opb/opc/opd (MedMCQA).
        options_fields = f.get("options_fields")
        if options_fields:
            vals = [hf.get_field(r, of) for of in options_fields]
            if all(v is not None for v in vals):
                return [str(v) for v in vals]
        # 3) correct + incorrect(s): assemble + deterministically rotate (GPQA).
        correct = hf.get_field(r, f.get("correct"))
        incorrect = hf.get_field(r, f.get("incorrect"))
        inc_fields = f.get("incorrect_fields")
        if correct is not None and (incorrect is not None or inc_fields):
            if inc_fields:
                inc = [hf.get_field(r, x) for x in inc_fields]
            else:
                inc = incorrect if isinstance(incorrect, list) else [incorrect]
            inc = [str(x) for x in inc if x is not None]
            options = [str(correct)] + inc
            rid = str(hf.get_field(r, f.get("id")) or r.get("id") or "")
            shift = (sum(ord(c) for c in rid) % len(options)) if options else 0
            options = options[shift:] + options[:shift]
            r["_gold_text"] = str(correct)  # stash for gold resolution
            return options
        return None

    def _build_constraints(self, r: Dict, f: Dict) -> Any:
        ids = hf.get_field(r, f.get("instruction_id_list"))
        kwargs = hf.get_field(r, f.get("kwargs"))
        if ids is not None:
            return {"instruction_id_list": ids, "kwargs": kwargs or []}
        return hf.get_field(r, f.get("constraints"))

    # --- running ------------------------------------------------------------

    def run_instance(self, instance, target, ctx: RunContext, out_dir: Path) -> Dict:
        provider = target["provider"]
        ws = out_dir / "workspace"
        if ws.exists():
            shutil.rmtree(ws)
        ws.mkdir(parents=True, exist_ok=True)
        logs = out_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)

        # MCQ gold may have been computed during choice assembly.
        gold = instance.gold
        if self.mode == "mcq" and instance.raw.get("_gold_text") is not None:
            gold = instance.raw["_gold_text"]

        prompt = self._build_prompt(instance)
        executor = make_executor(ctx, ws, ws, instance.id, provider)
        record = base_record(instance, target, ctx, self.name)
        try:
            session = f"obq-{safe_id(instance.id)[:16]}-{provider[:8]}-{int(time.time())}"
            pr = get_provider(provider).run_task(
                prompt=prompt,
                workdir=executor.container_workspace(),
                provider_model=target["provider_model"],
                session_name=session,
                executor=executor,
            )
            write_text(logs / "provider.stdout.log", pr.stdout or "")
            write_text(logs / "provider.stderr.log", pr.stderr or "")
            write_text(logs / "provider.raw.jsonl", pr.raw_output or "")

            pricing = ctx.models_cfg.get("models", {}).get(target["benchmark_model"], {}).get(
                "pricing"
            )
            apply_provider_result(record, pr, pricing)

            objective, mode_detail, gate = self._verdict(instance, pr, ws, gold)
            set_verdict(record, objective, self.mode, mode_detail)
            write_text(logs / "verdict.txt", gate)

            if self.run_judge_flag or self.mode == "judge_text":
                provider_ev = get_provider(provider).build_provider_evidence(pr)
                answer = (
                    pr.stdout
                    if self.mode == "constraint"
                    else verify.read_answer(executor.workspace_host_path(), pr.stdout)
                )
                evidence = (
                    f"<agent_answer>\n{(answer or '')[:8000]}\n</agent_answer>\n"
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
        finally:
            executor.close()

        log(
            f"[bench] {self.name} {instance.id} {provider} "
            f"objective={record['verdict']['objective']} judge={record['judge'].get('score')}",
            ctx.verbosity,
            "normal",
        )
        return record

    # --- internals ----------------------------------------------------------

    def _build_prompt(self, instance: Instance) -> str:
        system = instance.system_prompt or DOMAIN_SYSTEM.get(
            self.domain, DOMAIN_SYSTEM[""]
        )
        body = instance.prompt
        if self.mode == "mcq" and instance.choices:
            labeled = "\n".join(
                f"{_LETTERS[i]}. {c}" for i, c in enumerate(instance.choices)
            )
            body = (
                f"{instance.prompt}\n\nChoices:\n{labeled}\n\n"
                "Select the single correct choice. When finished, write ONLY the letter "
                "of your chosen answer (e.g. `C`) to a file named `answer.txt` in your "
                "current working directory."
            )
        elif self.mode == "final_answer":
            body = (
                f"{instance.prompt}\n\nSolve the problem. When finished, write ONLY your "
                "final answer (no working, no units unless required) to a file named "
                "`answer.txt` in your current working directory."
            )
        elif self.mode == "judge_text":
            body = (
                f"{instance.prompt}\n\nWhen finished, write your complete final response "
                "to a file named `answer.txt` in your current working directory."
            )
        # constraint mode: the prompt itself carries the instructions; do not add a
        # file directive (it would alter the response we must grade).
        return f"System:\n{system}\n\nInstruction:\n{body}\n"

    def _verdict(self, instance, pr, ws: Path, gold):
        if self.mode == "mcq":
            answer = verify.read_answer(ws, pr.stdout)
            ok = verify.mcq_match(answer, gold, instance.choices or [])
            gl = verify.gold_letter(gold, instance.choices or [])
            cl = verify.chosen_letter(answer, instance.choices or [])
            detail = {"gold": gl, "chosen": cl}
            gate = (
                "OBJECTIVE GATE (authoritative, source of truth):\n"
                f"correct={ok}\ngold={gl} chosen={cl}\n"
                "The letter match determines correctness; judge the response quality."
            )
            return ok, detail, gate
        if self.mode == "final_answer":
            answer = verify.read_answer(ws, pr.stdout)
            ok = verify.final_answer_match(answer, gold, self.match_mode)
            extracted = verify.extract_final(answer)
            detail = {"expected": str(gold), "extracted": extracted, "match": self.match_mode}
            gate = (
                "OBJECTIVE GATE (authoritative, source of truth):\n"
                f"correct={ok}\nexpected={gold}\nextracted={extracted}\n"
                "The answer match determines correctness; judge the reasoning quality."
            )
            return ok, detail, gate
        if self.mode == "constraint":
            objective, detail = verify.verify_constraints(pr.stdout, instance.constraints)
            gate = (
                "CONSTRAINT GATE (programmatic instruction-following check):\n"
                f"passed={objective}\nrecognized={detail.get('recognized')}\n"
                f"results={detail.get('results')}"
            )
            return objective, detail, gate
        # judge_text: no objective gate; hand the rubric/reference to the judge.
        gate = (
            "GRADING RUBRIC (use to score 0-100):\n"
            f"{instance.rubric or 'Judge correctness, completeness, and quality.'}\n\n"
            f"REFERENCE ANSWER (may be partial):\n{instance.reference or '(none provided)'}"
        )
        return None, {"reference": bool(instance.reference)}, gate
