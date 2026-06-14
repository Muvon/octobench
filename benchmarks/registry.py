"""Benchmark registry: resolve a name/config to an adapter instance.

A benchmark is a YAML file under configs/benchmarks/ with an `engine` key binding
it to one of the adapter engines below. `--benchmark <name>` resolves to
configs/benchmarks/<name>.yaml; a path ending in .yaml is loaded directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from benchmarks.base import BenchmarkAdapter
from benchmarks.docker_task import DockerTaskAdapter
from benchmarks.qa import QAAdapter
from benchmarks.swebench_live import SwebenchLiveAdapter

ENGINES = {
    "qa": QAAdapter,
    "docker_task": DockerTaskAdapter,
    "swebench_live": SwebenchLiveAdapter,
}

CONFIG_SUBDIR = Path("configs") / "benchmarks"


def config_dir(repo_root: Path) -> Path:
    return repo_root / CONFIG_SUBDIR


def load_config(repo_root: Path, name_or_path: str) -> Dict:
    p = Path(name_or_path)
    if p.suffix == ".yaml" and p.exists():
        path = p
    else:
        path = config_dir(repo_root) / f"{name_or_path}.yaml"
    if not path.exists():
        raise RuntimeError(f"benchmark config not found: {path}")
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("name", path.stem)
    if "engine" not in cfg:
        raise RuntimeError(f"benchmark config {path} missing required 'engine' key")
    if cfg["engine"] not in ENGINES:
        raise RuntimeError(
            f"benchmark config {path} has unknown engine '{cfg['engine']}' "
            f"(known: {', '.join(sorted(ENGINES))})"
        )
    return cfg


def build_adapter(repo_root: Path, name_or_path: str) -> BenchmarkAdapter:
    cfg = load_config(repo_root, name_or_path)
    return ENGINES[cfg["engine"]](cfg)


def list_benchmarks(repo_root: Path) -> List[Tuple[str, Dict]]:
    """Return (name, config) for every benchmark config, sorted by domain+name."""
    out: List[Tuple[str, Dict]] = []
    d = config_dir(repo_root)
    if not d.exists():
        return out
    for path in sorted(d.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            cfg = {"_error": "unreadable"}
        cfg.setdefault("name", path.stem)
        out.append((path.stem, cfg))
    out.sort(key=lambda x: (x[1].get("domain", ""), x[0]))
    return out
